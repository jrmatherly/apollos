"""Apollos AI as MCP Server — Streamable HTTP transport.

External MCP clients (VS Code, Cursor, Claude Desktop) connect here
to use Apollos AI's search, chat, and content tools.
"""

import json
import logging

from asgiref.sync import sync_to_async
from fastapi import APIRouter, HTTPException, Request

from apollos.utils.mcp_jwt import get_mcp_scopes, get_user_from_mcp_token, validate_mcp_token

logger = logging.getLogger(__name__)
mcp_server_router = APIRouter(prefix="/mcp/v1", tags=["mcp-server"])


async def authenticate_mcp_request(request: Request):
    """Authenticate inbound MCP request via Entra ID JWT."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(401, "Missing or invalid Authorization header")

    token = auth_header.split("Bearer ", 1)[1]
    try:
        claims = validate_mcp_token(token)
    except Exception as e:
        logger.warning(f"MCP JWT validation failed: {e}")
        raise HTTPException(401, "Invalid token")

    user = await sync_to_async(get_user_from_mcp_token)(claims)
    if not user:
        raise HTTPException(403, "User not found. Must log in via SSO first.")

    scopes = get_mcp_scopes(claims)
    return user, scopes


@mcp_server_router.post("/tools/list")
async def mcp_list_tools(request: Request):
    """MCP tools/list — Return available tools."""
    user, scopes = await authenticate_mcp_request(request)

    tools = []

    if "mcp:read" in scopes or "mcp:tools" in scopes:
        tools.extend(
            [
                {
                    "name": "search",
                    "description": "Search the Apollos AI knowledge base",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query"},
                            "max_results": {"type": "integer", "default": 5},
                        },
                        "required": ["query"],
                    },
                },
                {
                    "name": "chat",
                    "description": "Ask Apollos AI a question",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "message": {"type": "string", "description": "Your question"},
                        },
                        "required": ["message"],
                    },
                },
            ]
        )

    if "mcp:admin" in scopes:
        tools.append(
            {
                "name": "admin_status",
                "description": "Get Apollos AI server status",
                "inputSchema": {"type": "object", "properties": {}},
            }
        )

    return {"tools": tools}


@mcp_server_router.post("/tools/call")
async def mcp_call_tool(request: Request):
    """MCP tools/call — Execute a tool."""
    user, scopes = await authenticate_mcp_request(request)

    body = await request.json()
    tool_name = body.get("name")
    arguments = body.get("arguments", {})

    if tool_name == "search":
        if "mcp:read" not in scopes and "mcp:tools" not in scopes:
            raise HTTPException(403, "Insufficient scope for search")
        return await _handle_search(user, arguments)

    if tool_name == "chat":
        if "mcp:tools" not in scopes:
            raise HTTPException(403, "Insufficient scope for chat")
        return await _handle_chat(user, arguments)

    if tool_name == "admin_status":
        if "mcp:admin" not in scopes:
            raise HTTPException(403, "Insufficient scope for admin_status")
        return await _handle_admin_status()

    raise HTTPException(404, f"Tool not found: {tool_name}")


async def _handle_search(user, arguments):
    """Execute search tool."""
    from apollos.search_type.text_search import query as text_query

    raw_query = arguments.get("query", "")
    max_results = arguments.get("max_results", 5)

    try:
        compiled_results, _entries = await text_query(
            raw_query=raw_query,
            user=user,
            max_distance=None,
        )

        results = compiled_results[:max_results]
        return {
            "content": [{"type": "text", "text": json.dumps(results, default=str)}],
            "isError": False,
        }
    except Exception as e:
        logger.error(f"Search tool error: {e}")
        return {
            "content": [{"type": "text", "text": f"Search failed: {e}"}],
            "isError": True,
        }


async def _handle_chat(user, arguments):
    """Execute chat tool — simplified single-turn response."""
    message = arguments.get("message", "")
    return {
        "content": [{"type": "text", "text": f"Chat response for: {message} (implementation pending)"}],
        "isError": False,
    }


async def _handle_admin_status():
    """Return server status information."""
    from apollos.utils.state import state

    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(
                    {
                        "status": "running",
                        "device": str(state.device),
                        "anonymous_mode": state.anonymous_mode,
                    }
                ),
            }
        ],
        "isError": False,
    }
