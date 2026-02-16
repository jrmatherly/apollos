"""MCP Service Registry and Connection management endpoints."""

import logging
from typing import Optional

from asgiref.sync import sync_to_async
from django.db import models
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from starlette.authentication import requires

from apollos.database.models import McpServiceRegistry, McpUserConnection, Team

logger = logging.getLogger(__name__)
api_mcp = APIRouter(prefix="/api/mcp", tags=["mcp"])


class McpServiceCreate(BaseModel):
    name: str
    description: str = ""
    server_url: str
    service_type: str = "external"
    oauth_discovery_url: Optional[str] = None
    oauth_client_id: Optional[str] = None
    oauth_client_secret: Optional[str] = None
    oauth_scopes: Optional[str] = None
    supports_dcr: bool = False
    requires_admin_approval: bool = True
    enabled: bool = True
    icon_url: Optional[str] = None


@api_mcp.get("/services")
@requires(["authenticated"])
async def list_mcp_services(request: Request):
    """List available MCP services filtered by user's team access."""
    user = request.user.object

    if user.is_org_admin or user.is_staff:
        services = await sync_to_async(list)(McpServiceRegistry.objects.filter(enabled=True))
    else:
        # Filter by team access
        user_teams = await sync_to_async(list)(Team.objects.filter(memberships__user=user).values_list("id", flat=True))
        services = await sync_to_async(list)(
            McpServiceRegistry.objects.filter(
                enabled=True,
            )
            .filter(models.Q(allowed_teams__id__in=user_teams) | models.Q(allowed_teams__isnull=True))
            .distinct()
        )

    return [
        {
            "id": s.id,
            "name": s.name,
            "description": s.description,
            "service_type": s.service_type,
            "icon_url": s.icon_url,
            "requires_admin_approval": s.requires_admin_approval,
        }
        for s in services
    ]


@api_mcp.post("/services")
@requires(["authenticated"])
async def create_mcp_service(request: Request, body: McpServiceCreate):
    """Create a new MCP service (admin only)."""
    from apollos.configure import require_admin

    require_admin(request)

    # Encrypt client secret if provided
    encrypted_secret = None
    if body.oauth_client_secret:
        from apollos.utils.crypto import encrypt_token

        encrypted_secret = encrypt_token(body.oauth_client_secret)

    service = await McpServiceRegistry.objects.acreate(
        name=body.name,
        description=body.description,
        server_url=body.server_url,
        service_type=body.service_type,
        oauth_discovery_url=body.oauth_discovery_url,
        oauth_client_id=body.oauth_client_id,
        oauth_client_secret=encrypted_secret,
        oauth_scopes=body.oauth_scopes,
        supports_dcr=body.supports_dcr,
        requires_admin_approval=body.requires_admin_approval,
        enabled=body.enabled,
        icon_url=body.icon_url,
    )

    return {"id": service.id, "name": service.name, "status": "created"}


@api_mcp.delete("/services/{service_id}")
@requires(["authenticated"])
async def delete_mcp_service(request: Request, service_id: int):
    """Delete an MCP service (admin only)."""
    from apollos.configure import require_admin

    require_admin(request)

    deleted, _ = await McpServiceRegistry.objects.filter(id=service_id).adelete()
    if not deleted:
        raise HTTPException(404, "Service not found")
    return {"status": "deleted"}


@api_mcp.get("/connections")
@requires(["authenticated"])
async def list_user_connections(request: Request):
    """List user's MCP service connections."""
    user = request.user.object
    connections = await sync_to_async(list)(McpUserConnection.objects.filter(user=user).select_related("service"))
    return [
        {
            "service_id": c.service_id,
            "service_name": c.service.name,
            "status": c.status,
            "scopes_granted": c.scopes_granted,
            "last_used_at": c.last_used_at.isoformat() if c.last_used_at else None,
        }
        for c in connections
    ]


@api_mcp.post("/connect/{service_id}")
@requires(["authenticated"])
async def initiate_mcp_connection(request: Request, service_id: int):
    """Start OAuth flow to connect to an MCP service.

    Returns an authorization URL to redirect the user to.
    """
    user = request.user.object

    service = await sync_to_async(McpServiceRegistry.objects.filter(id=service_id, enabled=True).first)()
    if not service:
        raise HTTPException(404, "Service not found or disabled")

    from apollos.processor.tools.mcp_oauth import McpOAuthClient

    oauth_client = McpOAuthClient()

    auth_url = await oauth_client.start_auth_flow(service, user, request)
    return {"authorization_url": auth_url}


@api_mcp.delete("/connections/{service_id}")
@requires(["authenticated"])
async def disconnect_mcp_service(request: Request, service_id: int):
    """Disconnect from an MCP service (revoke tokens)."""
    user = request.user.object

    connection = await sync_to_async(McpUserConnection.objects.filter(user=user, service_id=service_id).first)()
    if not connection:
        raise HTTPException(404, "Connection not found")

    connection.status = McpUserConnection.Status.REVOKED
    connection.access_token = None
    connection.refresh_token = None
    await connection.asave()

    return {"status": "disconnected"}
