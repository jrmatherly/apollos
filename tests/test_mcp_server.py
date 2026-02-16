"""Tests for Apollos as MCP Server (inbound).

Tests cover:
- JWT validation logic
- Auth failures (missing/invalid/expired token, missing user)
- Scope-based tool filtering
- Protected Resource Metadata endpoint
- Search tool execution
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from asgiref.sync import sync_to_async

from tests.helpers import UserFactory

# ---------------------------------------------------------------------------
# JWT validation unit tests
# ---------------------------------------------------------------------------


class TestMcpAuthNoDb:
    """Verify MCP auth logic that requires no database."""

    def test_missing_authorization_header_raises(self):
        from fastapi import HTTPException

        from apollos.routers.api_mcp_server import authenticate_mcp_request

        request = MagicMock()
        request.headers = {}

        with pytest.raises(HTTPException) as exc_info:
            asyncio.get_event_loop().run_until_complete(authenticate_mcp_request(request))
        assert exc_info.value.status_code == 401

    def test_invalid_bearer_format_raises(self):
        from fastapi import HTTPException

        from apollos.routers.api_mcp_server import authenticate_mcp_request

        request = MagicMock()
        request.headers = {"Authorization": "Basic abc123"}

        with pytest.raises(HTTPException) as exc_info:
            asyncio.get_event_loop().run_until_complete(authenticate_mcp_request(request))
        assert exc_info.value.status_code == 401

    @patch("apollos.routers.api_mcp_server.validate_mcp_token")
    def test_invalid_jwt_returns_401(self, mock_validate):
        from fastapi import HTTPException

        from apollos.routers.api_mcp_server import authenticate_mcp_request

        mock_validate.side_effect = Exception("Invalid signature")

        request = MagicMock()
        request.headers = {"Authorization": "Bearer invalid.jwt.token"}

        with pytest.raises(HTTPException) as exc_info:
            asyncio.get_event_loop().run_until_complete(authenticate_mcp_request(request))
        assert exc_info.value.status_code == 401


@pytest.mark.django_db(transaction=True)
class TestMcpAuthWithDb:
    """Verify MCP auth logic that requires database access."""

    @pytest.mark.anyio
    @patch("apollos.routers.api_mcp_server.validate_mcp_token")
    @patch("apollos.routers.api_mcp_server.get_user_from_mcp_token")
    async def test_missing_user_returns_403(self, mock_get_user, mock_validate):
        from fastapi import HTTPException

        from apollos.routers.api_mcp_server import authenticate_mcp_request

        mock_validate.return_value = {"oid": "unknown-oid", "sub": "unknown-sub"}
        mock_get_user.return_value = None

        request = MagicMock()
        request.headers = {"Authorization": "Bearer valid.jwt.token"}

        with pytest.raises(HTTPException) as exc_info:
            await authenticate_mcp_request(request)
        assert exc_info.value.status_code == 403

    @pytest.mark.anyio
    @patch("apollos.routers.api_mcp_server.validate_mcp_token")
    @patch("apollos.routers.api_mcp_server.get_user_from_mcp_token")
    @patch("apollos.routers.api_mcp_server.get_mcp_scopes")
    async def test_valid_jwt_returns_user_and_scopes(self, mock_scopes, mock_get_user, mock_validate):
        from apollos.routers.api_mcp_server import authenticate_mcp_request

        user = await sync_to_async(UserFactory)()
        mock_validate.return_value = {"oid": "test-oid"}
        mock_get_user.return_value = user
        mock_scopes.return_value = ["mcp:read", "mcp:tools"]

        request = MagicMock()
        request.headers = {"Authorization": "Bearer valid.jwt.token"}

        result_user, result_scopes = await authenticate_mcp_request(request)
        assert result_user == user
        assert "mcp:read" in result_scopes
        assert "mcp:tools" in result_scopes

    @pytest.mark.anyio
    @patch("apollos.routers.api_mcp_server.validate_mcp_token")
    async def test_real_user_lookup_by_oid(self, mock_validate):
        """Integration test: exercises real sync_to_async ORM lookup."""
        from apollos.routers.api_mcp_server import authenticate_mcp_request

        await sync_to_async(UserFactory)(entra_oid="integration-oid-789")
        mock_validate.return_value = {"oid": "integration-oid-789", "sub": "sub-xyz", "scp": "mcp:read"}

        request = MagicMock()
        request.headers = {"Authorization": "Bearer valid.jwt.token"}

        result_user, result_scopes = await authenticate_mcp_request(request)
        assert result_user.entra_oid == "integration-oid-789"
        assert "mcp:read" in result_scopes


# ---------------------------------------------------------------------------
# Scope extraction
# ---------------------------------------------------------------------------


class TestGetMcpScopes:
    """Verify scope extraction from JWT claims."""

    def test_extracts_delegated_scopes(self):
        from apollos.utils.mcp_jwt import get_mcp_scopes

        claims = {"scp": "mcp:read mcp:tools"}
        scopes = get_mcp_scopes(claims)
        assert "mcp:read" in scopes
        assert "mcp:tools" in scopes

    def test_extracts_application_roles(self):
        from apollos.utils.mcp_jwt import get_mcp_scopes

        claims = {"roles": ["mcp:admin"]}
        scopes = get_mcp_scopes(claims)
        assert "mcp:admin" in scopes

    def test_combines_scp_and_roles(self):
        from apollos.utils.mcp_jwt import get_mcp_scopes

        claims = {"scp": "mcp:read", "roles": ["mcp:admin"]}
        scopes = get_mcp_scopes(claims)
        assert "mcp:read" in scopes
        assert "mcp:admin" in scopes

    def test_empty_claims_returns_empty(self):
        from apollos.utils.mcp_jwt import get_mcp_scopes

        scopes = get_mcp_scopes({})
        assert scopes == []


# ---------------------------------------------------------------------------
# User lookup from JWT claims
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
class TestGetUserFromMcpToken:
    """Verify user lookup from JWT claims."""

    def test_finds_user_by_oid(self):
        from apollos.utils.mcp_jwt import get_user_from_mcp_token

        user = UserFactory(entra_oid="test-oid-123")
        found = get_user_from_mcp_token({"oid": "test-oid-123"})
        assert found == user

    def test_falls_back_to_sub(self):
        from apollos.utils.mcp_jwt import get_user_from_mcp_token

        user = UserFactory(entra_oid="test-sub-456")
        found = get_user_from_mcp_token({"oid": "nonexistent", "sub": "test-sub-456"})
        assert found == user

    def test_returns_none_for_unknown_user(self):
        from apollos.utils.mcp_jwt import get_user_from_mcp_token

        found = get_user_from_mcp_token({"oid": "no-such-oid", "sub": "no-such-sub"})
        assert found is None


# ---------------------------------------------------------------------------
# Tool listing with scopes
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
class TestMcpListTools:
    """Verify tools/list respects scopes."""

    @pytest.mark.anyio
    @patch("apollos.routers.api_mcp_server.authenticate_mcp_request", new_callable=AsyncMock)
    async def test_read_scope_returns_search_and_chat(self, mock_auth):
        from apollos.routers.api_mcp_server import mcp_list_tools

        user = await sync_to_async(UserFactory)()
        mock_auth.return_value = (user, ["mcp:read", "mcp:tools"])

        request = MagicMock()
        result = await mcp_list_tools(request)
        tool_names = [t["name"] for t in result["tools"]]
        assert "search" in tool_names
        assert "chat" in tool_names
        assert "admin_status" not in tool_names

    @pytest.mark.anyio
    @patch("apollos.routers.api_mcp_server.authenticate_mcp_request", new_callable=AsyncMock)
    async def test_admin_scope_includes_admin_tool(self, mock_auth):
        from apollos.routers.api_mcp_server import mcp_list_tools

        user = await sync_to_async(UserFactory)()
        mock_auth.return_value = (user, ["mcp:read", "mcp:tools", "mcp:admin"])

        request = MagicMock()
        result = await mcp_list_tools(request)
        tool_names = [t["name"] for t in result["tools"]]
        assert "admin_status" in tool_names

    @pytest.mark.anyio
    @patch("apollos.routers.api_mcp_server.authenticate_mcp_request", new_callable=AsyncMock)
    async def test_no_scopes_returns_empty_tools(self, mock_auth):
        from apollos.routers.api_mcp_server import mcp_list_tools

        user = await sync_to_async(UserFactory)()
        mock_auth.return_value = (user, [])

        request = MagicMock()
        result = await mcp_list_tools(request)
        assert result["tools"] == []


# ---------------------------------------------------------------------------
# Tool call scope enforcement
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
class TestMcpCallTool:
    """Verify tools/call enforces scope checks."""

    @pytest.mark.anyio
    @patch("apollos.routers.api_mcp_server.authenticate_mcp_request", new_callable=AsyncMock)
    async def test_search_without_scope_raises_403(self, mock_auth):
        from fastapi import HTTPException

        from apollos.routers.api_mcp_server import mcp_call_tool

        user = await sync_to_async(UserFactory)()
        mock_auth.return_value = (user, [])

        request = MagicMock()
        request.json = AsyncMock(return_value={"name": "search", "arguments": {"query": "test"}})

        with pytest.raises(HTTPException) as exc_info:
            await mcp_call_tool(request)
        assert exc_info.value.status_code == 403

    @pytest.mark.anyio
    @patch("apollos.routers.api_mcp_server.authenticate_mcp_request", new_callable=AsyncMock)
    async def test_unknown_tool_raises_404(self, mock_auth):
        from fastapi import HTTPException

        from apollos.routers.api_mcp_server import mcp_call_tool

        user = await sync_to_async(UserFactory)()
        mock_auth.return_value = (user, ["mcp:tools"])

        request = MagicMock()
        request.json = AsyncMock(return_value={"name": "nonexistent_tool", "arguments": {}})

        with pytest.raises(HTTPException) as exc_info:
            await mcp_call_tool(request)
        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# Protected Resource Metadata
# ---------------------------------------------------------------------------


class TestProtectedResourceMetadata:
    """Verify RFC 9728 metadata endpoint."""

    @pytest.mark.anyio
    async def test_returns_valid_metadata(self):
        from apollos.routers.api_mcp import protected_resource_metadata

        with (
            patch("django.conf.settings.APOLLOS_DOMAIN", "test.apollosai.dev", create=True),
            patch("apollos.utils.mcp_jwt.ENTRA_TENANT_ID", "test-tenant"),
            patch("apollos.utils.mcp_jwt.MCP_RESOURCE_URI", "api://apollos-mcp"),
            patch("apollos.utils.mcp_jwt.MCP_CLIENT_ID", "test-client-id"),
        ):
            result = await protected_resource_metadata()

        assert result["resource"] == "api://apollos-mcp"
        assert "authorization_servers" in result
        assert len(result["authorization_servers"]) == 1
        assert "test-tenant" in result["authorization_servers"][0]
        assert "mcp:read" in result["scopes_supported"]
        assert result["bearer_methods_supported"] == ["header"]
