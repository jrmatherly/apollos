"""Tests for Phase 7 hardening features.

Covers:
- Audit logging (model, utility, admin endpoint)
- Security headers middleware
- Health check endpoint (unauthenticated)
- CSRF origin middleware
"""

import json

import pytest
from asgiref.sync import sync_to_async

from apollos.database.models import ApollosUser, AuditLog
from apollos.utils.audit import audit_log
from tests.helpers import UserFactory

# ---------------------------------------------------------------------------
# Auth header for the `client` fixture (api_user token = "kk-secret")
# The client fixture's user is NOT an admin by default.
# ---------------------------------------------------------------------------
AUTH_HEADERS = {"Authorization": "Bearer kk-secret"}


def _make_admin(client):
    """Promote the client fixture's authenticated user to org admin."""
    response = client.get("/api/v1/user", headers=AUTH_HEADERS)
    data = response.json()
    user = ApollosUser.objects.get(username=data["username"])
    user.is_org_admin = True
    user.save()
    return user


# ---------------------------------------------------------------------------
# 1. Audit Logging Tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
class TestAuditLogCreation:
    """Verify the audit_log() utility creates database records."""

    @pytest.mark.anyio
    async def test_audit_log_creates_record(self):
        """audit_log() should create an AuditLog entry in the database."""
        user = await sync_to_async(UserFactory)()
        await audit_log(user=user, action="test.action", resource_type="test", resource_id="123")
        exists = await AuditLog.objects.filter(action="test.action").aexists()
        assert exists

    @pytest.mark.anyio
    async def test_audit_log_stores_details(self):
        """audit_log() should store arbitrary JSON details."""
        user = await sync_to_async(UserFactory)()
        await audit_log(
            user=user,
            action="test.details",
            resource_type="test",
            details={"key": "value", "count": 42},
        )
        log = await AuditLog.objects.filter(action="test.details").afirst()
        assert log is not None
        assert log.details["key"] == "value"
        assert log.details["count"] == 42

    @pytest.mark.anyio
    async def test_audit_log_without_user(self):
        """audit_log() should work without a user (anonymous actions)."""
        await audit_log(action="test.anonymous", resource_type="system")
        exists = await AuditLog.objects.filter(action="test.anonymous").aexists()
        assert exists

    @pytest.mark.anyio
    async def test_audit_log_swallows_errors(self):
        """audit_log() should never raise exceptions, even with bad input."""
        # Pass None for action — the DB has max_length=100 and db_index so
        # extreme values could error, but audit_log should catch it.
        try:
            await audit_log(action="x" * 200, resource_type="test")
        except Exception:
            pytest.fail("audit_log() raised an exception instead of swallowing it")

    @pytest.mark.anyio
    async def test_audit_log_stores_resource_id(self):
        """audit_log() should store the resource_id as a string."""
        user = await sync_to_async(UserFactory)()
        await audit_log(user=user, action="test.resource", resource_type="team", resource_id="my-slug")
        log = await AuditLog.objects.filter(action="test.resource").afirst()
        assert log is not None
        assert log.resource_id == "my-slug"


@pytest.mark.django_db(transaction=True)
class TestAuditLogAdminEndpoint:
    """Test the GET /api/admin/audit-log endpoint."""

    def test_admin_can_view_audit_logs(self, client):
        """Admin user can access the audit-log endpoint."""
        _make_admin(client)
        response = client.get("/api/admin/audit-log", headers=AUTH_HEADERS)
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_non_admin_cannot_view_audit_logs(self, client):
        """Non-admin user gets 403 on audit-log endpoint."""
        response = client.get("/api/admin/audit-log", headers=AUTH_HEADERS)
        assert response.status_code == 403

    def test_audit_log_with_action_filter(self, client):
        """Audit log endpoint supports filtering by action prefix."""
        _make_admin(client)
        response = client.get("/api/admin/audit-log?action=auth", headers=AUTH_HEADERS)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # All returned entries should have actions starting with "auth"
        for entry in data:
            assert entry["action"].startswith("auth")

    def test_audit_log_pagination(self, client):
        """Audit log endpoint supports limit and offset."""
        _make_admin(client)
        response = client.get("/api/admin/audit-log?limit=5&offset=0", headers=AUTH_HEADERS)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 5

    def test_audit_log_response_shape(self, client):
        """Each audit log entry has the expected fields."""
        admin_user = _make_admin(client)
        # Create an audit log so there is at least one entry
        AuditLog.objects.create(
            user=admin_user,
            action="test.shape",
            resource_type="test",
            resource_id="1",
            details={"info": "test"},
        )
        response = client.get("/api/admin/audit-log?action=test.shape", headers=AUTH_HEADERS)
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        entry = data[0]
        assert "id" in entry
        assert "user" in entry
        assert "action" in entry
        assert "resource_type" in entry
        assert "created_at" in entry


# ---------------------------------------------------------------------------
# 2. Security Headers Tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
class TestSecurityHeaders:
    """Verify SecurityHeadersMiddleware adds headers to all responses."""

    def test_api_has_nosniff(self, client):
        """API responses include X-Content-Type-Options: nosniff."""
        response = client.get("/api/health", headers=AUTH_HEADERS)
        assert response.headers.get("x-content-type-options") == "nosniff"

    def test_api_has_frame_deny(self, client):
        """API responses include X-Frame-Options: DENY."""
        response = client.get("/api/health", headers=AUTH_HEADERS)
        assert response.headers.get("x-frame-options") == "DENY"

    def test_api_has_referrer_policy(self, client):
        """API responses include a strict Referrer-Policy."""
        response = client.get("/api/health", headers=AUTH_HEADERS)
        assert response.headers.get("referrer-policy") == "strict-origin-when-cross-origin"

    def test_api_has_xss_protection_disabled(self, client):
        """X-XSS-Protection should be 0 per modern best practice."""
        response = client.get("/api/health", headers=AUTH_HEADERS)
        assert response.headers.get("x-xss-protection") == "0"

    def test_api_has_permissions_policy(self, client):
        """API responses include a Permissions-Policy header."""
        response = client.get("/api/health", headers=AUTH_HEADERS)
        assert response.headers.get("permissions-policy") is not None

    def test_api_route_has_csp(self, client):
        """API routes get a strict Content-Security-Policy."""
        response = client.get("/api/health", headers=AUTH_HEADERS)
        assert response.headers.get("content-security-policy") == "default-src 'none'"

    def test_health_endpoint_has_security_headers(self, client):
        """The unauthenticated /health endpoint also gets security headers."""
        response = client.get("/health")
        assert response.headers.get("x-content-type-options") == "nosniff"
        assert response.headers.get("x-frame-options") == "DENY"


# ---------------------------------------------------------------------------
# 3. Health Check Tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
class TestHealthCheck:
    """Test the unauthenticated /health endpoint."""

    def test_health_unauthenticated(self, client):
        """Health endpoint works without any authentication."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_returns_status(self, client):
        """Health check returns structured status with checks."""
        response = client.get("/health")
        data = response.json()
        assert "status" in data
        assert "checks" in data
        assert data["checks"].get("database") == "ok"

    def test_health_status_healthy(self, client):
        """When database is up, status should be 'healthy'."""
        response = client.get("/health")
        data = response.json()
        assert data["status"] == "healthy"

    def test_authenticated_health_still_works(self, client):
        """The old /api/health (authenticated) should still work."""
        response = client.get("/api/health", headers=AUTH_HEADERS)
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# 4. CSRF Protection Tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
class TestCSRFProtection:
    """Test CSRFOriginMiddleware blocks cross-origin state-changing requests."""

    def test_csrf_blocks_cross_origin_post_to_non_api(self, client):
        """Cross-origin POST to non-API routes should be blocked with 403."""
        response = client.post(
            "/server/some-route",
            headers={"Origin": "https://evil.example.com"},
        )
        # 403 means CSRF blocked it (the route may not exist, but CSRF fires first)
        assert response.status_code == 403

    def test_csrf_allows_api_routes(self, client):
        """API routes skip CSRF checks (they use bearer tokens)."""
        # GET requests do not trigger CSRF
        response = client.get(
            "/api/health",
            headers={**AUTH_HEADERS, "Origin": "https://evil.example.com"},
        )
        assert response.status_code == 200

    def test_csrf_allows_api_post_with_cross_origin(self, client):
        """POST to /api/* routes should not be blocked by CSRF (bearer auth)."""
        response = client.post(
            "/api/chat",
            content=json.dumps({"q": "hello"}),
            headers={**AUTH_HEADERS, "Content-Type": "application/json", "Origin": "https://evil.example.com"},
        )
        # Should not be 403 (CSRF), may be 422/400/etc depending on validation
        assert response.status_code != 403

    def test_csrf_allows_localhost_origin(self, client):
        """Localhost origin should be allowed through CSRF check."""
        response = client.post(
            "/server/some-route",
            headers={"Origin": "http://localhost:42110"},
        )
        # Should NOT be 403 (CSRF block) — expect 404 (route not found) or similar
        assert response.status_code != 403

    def test_csrf_allows_127_origin(self, client):
        """127.0.0.1 origin should be allowed through CSRF check."""
        response = client.post(
            "/server/some-route",
            headers={"Origin": "http://127.0.0.1:42110"},
        )
        assert response.status_code != 403

    def test_csrf_allows_get_with_evil_origin(self, client):
        """GET requests should never be blocked by CSRF regardless of Origin."""
        response = client.get(
            "/health",
            headers={"Origin": "https://evil.example.com"},
        )
        assert response.status_code == 200

    def test_csrf_blocks_put_from_evil_origin(self, client):
        """PUT to non-API routes from evil origin should be blocked."""
        response = client.put(
            "/server/some-route",
            headers={"Origin": "https://evil.example.com"},
        )
        assert response.status_code == 403

    def test_csrf_blocks_delete_from_evil_origin(self, client):
        """DELETE to non-API routes from evil origin should be blocked."""
        response = client.delete(
            "/server/some-route",
            headers={"Origin": "https://evil.example.com"},
        )
        assert response.status_code == 403
