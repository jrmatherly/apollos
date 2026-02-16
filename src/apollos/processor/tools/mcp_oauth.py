"""Manual OAuth 2.1 + PKCE flow for external MCP services.

Does NOT use the MCP SDK's OAuthClientProvider — that's designed for CLI apps.
Implements discovery, PKCE, and token exchange manually for web app flow.
"""

import base64
import hashlib
import logging
import secrets
from urllib.parse import urlencode

import httpx
from django.conf import settings

from apollos.database.models import ApollosUser, McpServiceRegistry, McpUserConnection
from apollos.utils.crypto import decrypt_token, encrypt_token

logger = logging.getLogger(__name__)

APOLLOS_DOMAIN = getattr(settings, "APOLLOS_DOMAIN", "localhost")


class McpOAuthClient:
    """Handles OAuth 2.1 flows for external MCP services."""

    async def discover(self, server_url: str) -> dict:
        """OAuth/OIDC discovery per MCP spec.

        Try /.well-known/oauth-authorization-server first,
        then /.well-known/openid-configuration.
        """
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Try OAuth AS Metadata (RFC 8414) first
            resp = await client.get(f"{server_url}/.well-known/oauth-authorization-server")
            if resp.status_code == 200:
                return resp.json()
            # Fallback to OIDC Discovery
            resp = await client.get(f"{server_url}/.well-known/openid-configuration")
            if resp.status_code == 200:
                return resp.json()
        raise ValueError(f"No OAuth metadata found at {server_url}")

    async def start_auth_flow(self, service: McpServiceRegistry, user: ApollosUser, request) -> str:
        """Initiate OAuth 2.1 + PKCE flow. Returns authorization URL."""
        # Discover OAuth metadata if needed
        metadata = {}
        if service.oauth_discovery_url:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(service.oauth_discovery_url)
                if resp.status_code == 200:
                    metadata = resp.json()

        if not metadata:
            try:
                metadata = await self.discover(service.server_url)
            except ValueError:
                # Fall back to pre-configured endpoints
                pass

        authorization_endpoint = metadata.get("authorization_endpoint", f"{service.server_url}/authorize")

        # PKCE (required by OAuth 2.1)
        code_verifier = secrets.token_urlsafe(64)
        code_challenge = base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode()).digest()).rstrip(b"=").decode()

        # Generate state for CSRF protection
        state = secrets.token_urlsafe(32)

        # Store PKCE verifier and state in session
        request.session[f"mcp_pkce_{state}"] = code_verifier
        request.session[f"mcp_service_{state}"] = service.id

        # Get client_id
        client_id = service.oauth_client_id
        if not client_id and service.supports_dcr:
            client_id = await self._dynamic_client_registration(
                metadata.get("registration_endpoint"),
                service,
            )

        if not client_id:
            raise ValueError(f"No client_id configured for {service.name}")

        redirect_uri = f"https://{APOLLOS_DOMAIN}/auth/mcp/callback"
        if getattr(settings, "APOLLOS_NO_HTTPS", False):
            redirect_uri = "http://localhost:42110/auth/mcp/callback"

        params = {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": service.oauth_scopes or "read write",
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }

        return f"{authorization_endpoint}?{urlencode(params)}"

    async def exchange_code(self, service: McpServiceRegistry, code: str, code_verifier: str) -> dict:
        """Exchange authorization code for tokens."""
        metadata = {}
        if service.oauth_discovery_url:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(service.oauth_discovery_url)
                if resp.status_code == 200:
                    metadata = resp.json()

        token_endpoint = metadata.get("token_endpoint", f"{service.server_url}/token")

        redirect_uri = f"https://{APOLLOS_DOMAIN}/auth/mcp/callback"
        if getattr(settings, "APOLLOS_NO_HTTPS", False):
            redirect_uri = "http://localhost:42110/auth/mcp/callback"

        # Decrypt client secret
        client_secret = None
        if service.oauth_client_secret:
            client_secret = decrypt_token(service.oauth_client_secret)

        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": service.oauth_client_id,
            "code_verifier": code_verifier,
        }
        if client_secret:
            data["client_secret"] = client_secret

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(token_endpoint, data=data)
            if resp.status_code != 200:
                logger.error(f"Token exchange failed: {resp.status_code}")
                raise ValueError(f"Token exchange failed: {resp.status_code}")
            return resp.json()

    async def refresh_access_token(self, connection: McpUserConnection) -> bool:
        """Refresh an expired access token. Returns True if successful."""
        if not connection.refresh_token:
            return False

        service = connection.service
        refresh_token = decrypt_token(connection.refresh_token)

        metadata = {}
        if service.oauth_discovery_url:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(service.oauth_discovery_url)
                if resp.status_code == 200:
                    metadata = resp.json()

        token_endpoint = metadata.get("token_endpoint", f"{service.server_url}/token")

        client_secret = None
        if service.oauth_client_secret:
            client_secret = decrypt_token(service.oauth_client_secret)

        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": service.oauth_client_id,
        }
        if client_secret:
            data["client_secret"] = client_secret

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(token_endpoint, data=data)
            if resp.status_code != 200:
                connection.status = McpUserConnection.Status.ERROR
                connection.error_message = f"Refresh failed: {resp.status_code}"
                await connection.asave()
                return False

            tokens = resp.json()
            connection.access_token = encrypt_token(tokens["access_token"])
            if "refresh_token" in tokens:
                connection.refresh_token = encrypt_token(tokens["refresh_token"])
            if "expires_in" in tokens:
                from datetime import timedelta

                from django.utils import timezone

                connection.token_expires_at = timezone.now() + timedelta(seconds=tokens["expires_in"])
            connection.status = McpUserConnection.Status.CONNECTED
            connection.error_message = None
            await connection.asave()
            return True

    async def _dynamic_client_registration(self, registration_endpoint: str, service: McpServiceRegistry) -> str | None:
        """Dynamic Client Registration (RFC 7591)."""
        if not registration_endpoint:
            return None

        redirect_uri = f"https://{APOLLOS_DOMAIN}/auth/mcp/callback"

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                registration_endpoint,
                json={
                    "client_name": f"Apollos AI - {service.name}",
                    "redirect_uris": [redirect_uri],
                    "grant_types": ["authorization_code", "refresh_token"],
                    "response_types": ["code"],
                    "token_endpoint_auth_method": "client_secret_post",
                },
            )
            if resp.status_code in (200, 201):
                data = resp.json()
                # Save the registered client_id back to the service
                service.oauth_client_id = data.get("client_id")
                if data.get("client_secret"):
                    service.oauth_client_secret = encrypt_token(data["client_secret"])
                await service.asave()
                return service.oauth_client_id

        return None
