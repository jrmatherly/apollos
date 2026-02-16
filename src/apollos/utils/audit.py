"""Audit logging for security-relevant actions."""

import logging

from apollos.database.models import AuditLog

logger = logging.getLogger(__name__)


async def audit_log(
    user=None,
    action: str = "",
    resource_type: str = "",
    resource_id: str = "",
    details: dict | None = None,
    request=None,
):
    """Create an audit log entry. Swallows errors to never block the caller.

    Actions:
    - auth.login, auth.logout, auth.login_failed
    - entry.create, entry.delete, entry.share
    - agent.create, agent.delete
    - team.member_add, team.member_remove
    - mcp.connect, mcp.disconnect, mcp.tool_call
    - admin.model_change, admin.org_settings
    """
    ip_address = None
    user_agent = None
    if request:
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent", "")[:500]

    try:
        await AuditLog.objects.acreate(
            user=user,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else "",
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
        )
    except Exception as e:
        logger.error(f"Failed to create audit log: {e}")
