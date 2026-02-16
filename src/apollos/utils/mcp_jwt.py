"""JWT validation for inbound MCP requests using Entra ID JWKS."""

import logging
import os
from functools import lru_cache

import jwt as pyjwt

logger = logging.getLogger(__name__)

MCP_CLIENT_ID = os.environ.get("APOLLOS_MCP_CLIENT_ID", "")
MCP_RESOURCE_URI = os.environ.get("APOLLOS_MCP_RESOURCE_URI", "")
ENTRA_TENANT_ID = os.environ.get("APOLLOS_ENTRA_TENANT_ID", "")

JWKS_URI = f"https://login.microsoftonline.com/{ENTRA_TENANT_ID}/discovery/v2.0/keys"
ISSUER = f"https://login.microsoftonline.com/{ENTRA_TENANT_ID}/v2.0"


@lru_cache(maxsize=1)
def _get_jwks_client():
    """Get a cached JWKS client for Entra ID."""
    return pyjwt.PyJWKClient(JWKS_URI, cache_keys=True, lifespan=3600)


def validate_mcp_token(token: str) -> dict:
    """Validate a JWT from an inbound MCP client request.

    Returns decoded claims if valid.
    Raises jwt.InvalidTokenError (or subclass) if invalid.
    """
    jwks_client = _get_jwks_client()
    signing_key = jwks_client.get_signing_key_from_jwt(token)

    claims = pyjwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        audience=MCP_RESOURCE_URI or MCP_CLIENT_ID,
        issuer=ISSUER,
        options={"require": ["exp", "iss", "aud", "sub", "oid"]},
    )

    return claims


def get_user_from_mcp_token(claims: dict):
    """Look up ApollosUser from MCP JWT claims.

    Uses 'oid' first (stable), falls back to 'sub' (pairwise).
    """
    from apollos.database.models import ApollosUser

    oid = claims.get("oid")
    if oid:
        user = ApollosUser.objects.filter(entra_oid=oid).first()
        if user:
            return user

    # Fallback to sub (only works for SSO-provisioned users)
    sub = claims.get("sub")
    if sub:
        user = ApollosUser.objects.filter(entra_oid=sub).first()
        if user:
            return user

    return None


def get_mcp_scopes(claims: dict) -> list[str]:
    """Extract MCP scopes from token claims.

    Entra ID uses 'scp' for delegated permissions, 'roles' for application permissions.
    """
    scopes = claims.get("scp", "").split() if claims.get("scp") else []
    roles = claims.get("roles", [])
    return scopes + roles
