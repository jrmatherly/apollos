"""OAuth callback handler for MCP service connections."""

import logging
from datetime import timedelta

from asgiref.sync import sync_to_async
from django.utils import timezone
from fastapi import APIRouter, Request
from starlette.authentication import requires
from starlette.responses import RedirectResponse

from apollos.database.models import McpServiceRegistry, McpUserConnection
from apollos.processor.tools.mcp_oauth import McpOAuthClient
from apollos.utils.crypto import encrypt_token

logger = logging.getLogger(__name__)
auth_mcp_router = APIRouter(tags=["mcp-auth"])


@auth_mcp_router.get("/auth/mcp/callback")
@requires(["authenticated"])
async def mcp_oauth_callback(request: Request):
    """Handle OAuth callback from external MCP service."""
    code = request.query_params.get("code")
    state = request.query_params.get("state")
    error = request.query_params.get("error")

    if error:
        logger.error(f"MCP OAuth error: {error}")
        return RedirectResponse(url=f"/settings?mcp_error={error}", status_code=302)

    if not code or not state:
        return RedirectResponse(url="/settings?mcp_error=missing_params", status_code=302)

    # Validate state and retrieve PKCE verifier
    code_verifier = request.session.pop(f"mcp_pkce_{state}", None)
    service_id = request.session.pop(f"mcp_service_{state}", None)

    if not code_verifier or not service_id:
        return RedirectResponse(url="/settings?mcp_error=invalid_state", status_code=302)

    # Look up service
    service = await sync_to_async(McpServiceRegistry.objects.filter(id=service_id).first)()
    if not service:
        return RedirectResponse(url="/settings?mcp_error=service_not_found", status_code=302)

    # Exchange code for tokens
    oauth_client = McpOAuthClient()
    try:
        tokens = await oauth_client.exchange_code(service, code, code_verifier)
    except Exception as e:
        logger.error(f"MCP token exchange failed: {e}")
        return RedirectResponse(url="/settings?mcp_error=token_exchange_failed", status_code=302)

    # Store encrypted tokens
    user = request.user.object
    connection, created = await sync_to_async(McpUserConnection.objects.update_or_create)(
        user=user,
        service=service,
        defaults={
            "access_token": encrypt_token(tokens["access_token"]),
            "refresh_token": encrypt_token(tokens["refresh_token"]) if tokens.get("refresh_token") else None,
            "token_expires_at": timezone.now() + timedelta(seconds=tokens.get("expires_in", 3600)),
            "scopes_granted": tokens.get("scope", service.oauth_scopes),
            "status": McpUserConnection.Status.CONNECTED,
            "error_message": None,
        },
    )

    return RedirectResponse(url=f"/settings?mcp_connected={service.name}", status_code=302)
