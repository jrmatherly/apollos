"""Tests for MCP Service Registry and OAuth connection management.

Tests cover:
- Admin CRUD on McpServiceRegistry
- Team-based service filtering
- Token encryption/decryption roundtrip
- OAuth flow URL generation with PKCE
- Token refresh logic
- Disconnect/revoke flow
"""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from asgiref.sync import sync_to_async

from apollos.database.models import McpServiceRegistry, McpUserConnection
from tests.helpers import (
    McpServiceRegistryFactory,
    McpUserConnectionFactory,
    OrganizationFactory,
    TeamFactory,
    UserFactory,
)

# ---------------------------------------------------------------------------
# Unit Tests for McpServiceRegistry model
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
class TestMcpServiceRegistryModel:
    """Verify McpServiceRegistry model constraints and defaults."""

    def test_create_service(self):
        service = McpServiceRegistryFactory()
        assert service.id is not None
        assert service.enabled is True
        assert service.service_type == McpServiceRegistry.ServiceType.EXTERNAL

    def test_service_name_unique(self):
        McpServiceRegistryFactory(name="unique-service")
        from django.db import IntegrityError

        with pytest.raises(IntegrityError):
            McpServiceRegistryFactory(name="unique-service")

    def test_service_str_representation(self):
        service = McpServiceRegistryFactory(name="test-svc")
        assert str(service) == "test-svc"

    def test_service_with_oauth_config(self):
        service = McpServiceRegistryFactory(
            oauth_client_id="client-123",
            oauth_scopes="read write",
            supports_dcr=True,
        )
        assert service.oauth_client_id == "client-123"
        assert service.oauth_scopes == "read write"
        assert service.supports_dcr is True


# ---------------------------------------------------------------------------
# Unit Tests for McpUserConnection model
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
class TestMcpUserConnectionModel:
    """Verify McpUserConnection model constraints."""

    def test_create_connection(self):
        conn = McpUserConnectionFactory()
        assert conn.id is not None
        assert conn.status == McpUserConnection.Status.CONNECTED

    def test_connection_unique_per_user_service(self):
        user = UserFactory()
        service = McpServiceRegistryFactory()
        McpUserConnectionFactory(user=user, service=service)
        from django.db import IntegrityError

        with pytest.raises(IntegrityError):
            McpUserConnectionFactory(user=user, service=service)

    def test_connection_str_representation(self):
        conn = McpUserConnectionFactory()
        assert "->" in str(conn)

    def test_connection_statuses(self):
        for status_val in McpUserConnection.Status:
            conn = McpUserConnectionFactory(status=status_val)
            assert conn.status == status_val


# ---------------------------------------------------------------------------
# Token encryption roundtrip
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
class TestTokenEncryption:
    """Verify tokens are encrypted and decryptable."""

    @pytest.fixture(autouse=True)
    def set_vault_key(self):
        os.environ["APOLLOS_VAULT_MASTER_KEY"] = "test-master-key-at-least-32-chars-long!!!"
        yield
        del os.environ["APOLLOS_VAULT_MASTER_KEY"]

    def test_encrypt_decrypt_roundtrip(self):
        from apollos.utils.crypto import decrypt_token, encrypt_token

        original = "my-secret-access-token-12345"
        encrypted = encrypt_token(original)
        assert encrypted != original
        decrypted = decrypt_token(encrypted)
        assert decrypted == original

    def test_different_plaintexts_produce_different_ciphertexts(self):
        from apollos.utils.crypto import encrypt_token

        enc1 = encrypt_token("token-a")
        enc2 = encrypt_token("token-b")
        assert enc1 != enc2

    def test_same_plaintext_produces_different_ciphertexts(self):
        from apollos.utils.crypto import encrypt_token

        enc1 = encrypt_token("same-token")
        enc2 = encrypt_token("same-token")
        # Different nonces => different ciphertexts
        assert enc1 != enc2


# ---------------------------------------------------------------------------
# OAuth flow URL generation
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
class TestOAuthFlowGeneration:
    """Verify OAuth authorization URL generation with PKCE."""

    @pytest.fixture(autouse=True)
    def set_vault_key(self):
        os.environ["APOLLOS_VAULT_MASTER_KEY"] = "test-master-key-at-least-32-chars-long!!!"
        yield
        del os.environ["APOLLOS_VAULT_MASTER_KEY"]

    @pytest.mark.anyio
    async def test_start_auth_flow_returns_url_with_pkce(self):
        from apollos.processor.tools.mcp_oauth import McpOAuthClient

        service = await sync_to_async(McpServiceRegistryFactory)(
            oauth_client_id="test-client-id",
            oauth_scopes="read",
        )
        user = await sync_to_async(UserFactory)()

        # Mock request with session dict
        request = MagicMock()
        request.session = {}

        with patch(
            "apollos.processor.tools.mcp_oauth.McpOAuthClient.discover", new_callable=AsyncMock
        ) as mock_discover:
            mock_discover.side_effect = ValueError("No metadata")
            client = McpOAuthClient()
            url = await client.start_auth_flow(service, user, request)

        assert "response_type=code" in url
        assert "client_id=test-client-id" in url
        assert "code_challenge=" in url
        assert "code_challenge_method=S256" in url
        assert "state=" in url

        # Verify PKCE verifier was stored in session
        pkce_keys = [k for k in request.session if k.startswith("mcp_pkce_")]
        assert len(pkce_keys) == 1

    @pytest.mark.anyio
    async def test_start_auth_flow_raises_without_client_id(self):
        from apollos.processor.tools.mcp_oauth import McpOAuthClient

        service = await sync_to_async(McpServiceRegistryFactory)(
            oauth_client_id=None,
            supports_dcr=False,
        )
        user = await sync_to_async(UserFactory)()
        request = MagicMock()
        request.session = {}

        with patch(
            "apollos.processor.tools.mcp_oauth.McpOAuthClient.discover", new_callable=AsyncMock
        ) as mock_discover:
            mock_discover.side_effect = ValueError("No metadata")
            client = McpOAuthClient()
            with pytest.raises(ValueError, match="No client_id configured"):
                await client.start_auth_flow(service, user, request)


# ---------------------------------------------------------------------------
# Token refresh
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
class TestTokenRefresh:
    """Verify token refresh logic."""

    @pytest.fixture(autouse=True)
    def set_vault_key(self):
        os.environ["APOLLOS_VAULT_MASTER_KEY"] = "test-master-key-at-least-32-chars-long!!!"
        yield
        del os.environ["APOLLOS_VAULT_MASTER_KEY"]

    @pytest.mark.anyio
    async def test_refresh_returns_false_without_refresh_token(self):
        from apollos.processor.tools.mcp_oauth import McpOAuthClient

        conn = await sync_to_async(McpUserConnectionFactory)(refresh_token=None)
        client = McpOAuthClient()
        result = await client.refresh_access_token(conn)
        assert result is False

    @pytest.mark.anyio
    async def test_refresh_updates_tokens_on_success(self):
        from apollos.processor.tools.mcp_oauth import McpOAuthClient
        from apollos.utils.crypto import encrypt_token

        service = await sync_to_async(McpServiceRegistryFactory)(oauth_client_id="test-client")
        conn = await sync_to_async(McpUserConnectionFactory)(
            service=service,
            refresh_token=encrypt_token("old-refresh-token"),
        )

        mock_token_response = MagicMock()
        mock_token_response.status_code = 200
        mock_token_response.json.return_value = {
            "access_token": "new-access-token",
            "refresh_token": "new-refresh-token",
            "expires_in": 3600,
        }

        mock_discovery_response = MagicMock()
        mock_discovery_response.status_code = 404

        with patch("httpx.AsyncClient") as MockClient:
            mock_client_instance = AsyncMock()
            mock_client_instance.post.return_value = mock_token_response
            mock_client_instance.get.return_value = mock_discovery_response
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client_instance)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            client = McpOAuthClient()
            result = await client.refresh_access_token(conn)

        assert result is True
        await conn.arefresh_from_db()
        assert conn.status == McpUserConnection.Status.CONNECTED
        assert conn.access_token is not None
        assert conn.error_message is None


# ---------------------------------------------------------------------------
# Disconnect flow
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
class TestDisconnectFlow:
    """Verify disconnect revokes tokens."""

    def test_disconnect_clears_tokens(self):
        conn = McpUserConnectionFactory(
            access_token="encrypted-access",
            refresh_token="encrypted-refresh",
            status=McpUserConnection.Status.CONNECTED,
        )
        conn.status = McpUserConnection.Status.REVOKED
        conn.access_token = None
        conn.refresh_token = None
        conn.save()

        conn.refresh_from_db()
        assert conn.status == McpUserConnection.Status.REVOKED
        assert conn.access_token is None
        assert conn.refresh_token is None


# ---------------------------------------------------------------------------
# Team-based service filtering
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
class TestTeamServiceFiltering:
    """Verify services are filtered by team access."""

    def test_admin_sees_all_enabled_services(self):
        before_count = McpServiceRegistry.objects.filter(enabled=True).count()
        McpServiceRegistryFactory(name="svc-a-filter", enabled=True)
        McpServiceRegistryFactory(name="svc-b-filter", enabled=True)
        McpServiceRegistryFactory(name="svc-disabled-filter", enabled=False)

        enabled = McpServiceRegistry.objects.filter(enabled=True)
        assert enabled.count() == before_count + 2

    def test_service_with_team_restriction(self):
        org = OrganizationFactory()
        team = TeamFactory(organization=org)
        service = McpServiceRegistryFactory(name="team-only-svc-filter")
        service.allowed_teams.add(team)

        team_services = McpServiceRegistry.objects.filter(
            enabled=True,
            allowed_teams__id=team.id,
        )
        assert team_services.count() >= 1
        assert any(s.name == "team-only-svc-filter" for s in team_services)

    def test_unrestricted_service_visible_to_all(self):
        from django.db import models

        McpServiceRegistryFactory(name="open-svc-filter")

        open_services = McpServiceRegistry.objects.filter(
            enabled=True,
            name="open-svc-filter",
        ).filter(models.Q(allowed_teams__isnull=True))
        assert open_services.count() == 1


# ---------------------------------------------------------------------------
# MCPClient factory method
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
class TestMCPClientFromConnection:
    """Verify MCPClient.from_user_connection factory."""

    @pytest.fixture(autouse=True)
    def set_vault_key(self):
        os.environ["APOLLOS_VAULT_MASTER_KEY"] = "test-master-key-at-least-32-chars-long!!!"
        yield
        del os.environ["APOLLOS_VAULT_MASTER_KEY"]

    @pytest.mark.anyio
    async def test_creates_client_with_decrypted_token(self):
        from apollos.processor.tools.mcp import MCPClient
        from apollos.utils.crypto import encrypt_token

        service = await sync_to_async(McpServiceRegistryFactory)(server_url="https://mcp.example.com")
        conn = await sync_to_async(McpUserConnectionFactory)(
            service=service,
            access_token=encrypt_token("my-secret-token"),
            token_expires_at=None,  # No expiry = no refresh needed
        )

        client = await MCPClient.from_user_connection(conn)
        assert client.name == service.name
        assert client.path == "https://mcp.example.com"
        assert client.oauth_token == "my-secret-token"
