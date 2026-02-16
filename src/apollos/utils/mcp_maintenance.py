"""Background jobs for MCP token maintenance."""

import asyncio
import logging
from datetime import timedelta

from django.utils import timezone

from apollos.database.models import McpUserConnection
from apollos.processor.tools.mcp_oauth import McpOAuthClient

logger = logging.getLogger(__name__)


async def _refresh_expiring_mcp_tokens():
    """Proactively refresh MCP tokens that expire within the next hour."""
    from asgiref.sync import sync_to_async

    try:
        threshold = timezone.now() + timedelta(hours=1)
        expiring = await sync_to_async(list)(
            McpUserConnection.objects.filter(
                status=McpUserConnection.Status.CONNECTED,
                token_expires_at__lt=threshold,
                refresh_token__isnull=False,
            ).select_related("service")
        )
    except Exception as e:
        logger.error(f"Failed to query expiring MCP tokens: {e}")
        return

    oauth_client = McpOAuthClient()
    for conn in expiring:
        try:
            success = await oauth_client.refresh_access_token(conn)
            if success:
                logger.info(f"Refreshed MCP token for {conn.user_id} -> {conn.service.name}")
            else:
                logger.warning(f"Failed to refresh MCP token for {conn.user_id} -> {conn.service.name}")
        except Exception as e:
            logger.error(f"Error refreshing MCP token: {e}")


def refresh_expiring_mcp_tokens():
    """Sync wrapper for apscheduler's BackgroundScheduler (runs in thread)."""
    asyncio.run(_refresh_expiring_mcp_tokens())
