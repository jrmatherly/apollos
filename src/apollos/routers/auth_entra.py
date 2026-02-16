"""Microsoft Entra ID OIDC authentication endpoints."""

import logging
import uuid
from urllib.parse import urlparse

from fastapi import APIRouter, Request
from starlette.responses import RedirectResponse

from apollos.utils.audit import audit_log
from apollos.utils.entra import (
    acquire_token_by_code,
    extract_user_claims,
    fetch_user_groups_from_graph,
    get_auth_url,
    get_msal_app,
    is_entra_configured,
    sync_team_memberships,
)

logger = logging.getLogger(__name__)
entra_router = APIRouter(prefix="/auth/entra", tags=["auth"])


def _safe_redirect_url(url: str) -> str:
    """Validate redirect URL is a safe relative path (prevent open redirects)."""
    if not url:
        return "/"
    parsed = urlparse(url)
    # Reject absolute URLs (with scheme or netloc) and protocol-relative URLs
    if parsed.scheme or parsed.netloc or url.startswith("//"):
        return "/"
    return url


@entra_router.get("/login")
async def entra_login(request: Request):
    """Redirect to Microsoft Entra ID login page."""
    if not is_entra_configured():
        return RedirectResponse(url="/login?error=sso_not_configured", status_code=302)

    msal_app = get_msal_app()
    next_url = _safe_redirect_url(request.query_params.get("next", "/"))
    auth_url = get_auth_url(msal_app, state=next_url)
    return RedirectResponse(url=auth_url, status_code=302)


@entra_router.get("/callback")
async def entra_callback(request: Request):
    """Handle Entra ID OAuth callback."""
    from asgiref.sync import sync_to_async

    from apollos.database.models import ApollosUser

    code = request.query_params.get("code")
    state = _safe_redirect_url(request.query_params.get("state", "/"))
    error = request.query_params.get("error")

    if error:
        logger.error(f"Entra ID auth error: {error} - {request.query_params.get('error_description')}")
        return RedirectResponse(url=f"/login?error={error}", status_code=302)

    if not code:
        return RedirectResponse(url="/login?error=no_code", status_code=302)

    # Exchange code for tokens
    msal_app = get_msal_app()
    token_response = acquire_token_by_code(msal_app, code)

    if "error" in token_response:
        logger.error(f"Token exchange error: {token_response}")
        await audit_log(
            action="auth.login_failed",
            resource_type="auth",
            details={"method": "entra_id", "error": "token_exchange_failed"},
            request=request,
        )
        return RedirectResponse(url="/login?error=token_exchange_failed", status_code=302)

    # Extract claims
    claims = extract_user_claims(token_response)

    if not claims["oid"]:
        return RedirectResponse(url="/login?error=missing_oid", status_code=302)

    # Upsert user (match on entra_oid)
    user = await sync_to_async(ApollosUser.objects.filter(entra_oid=claims["oid"]).first)()

    if user:
        # Update existing user
        user.email = claims["email"] or user.email
        user.display_name = claims["name"] or user.display_name
        user.entra_upn = claims["upn"] or user.entra_upn
        await user.asave(update_fields=["email", "display_name", "entra_upn"])
    else:
        # Create new user with collision-safe username
        base_username = claims["email"].split("@")[0] if claims["email"] else claims["oid"][:20]
        username = base_username
        # Handle username collision by appending a short UUID suffix
        while await sync_to_async(ApollosUser.objects.filter(username=username).exists)():
            username = f"{base_username}_{uuid.uuid4().hex[:6]}"
        user = await ApollosUser.objects.acreate(
            username=username,
            email=claims["email"],
            entra_oid=claims["oid"],
            entra_upn=claims["upn"],
            display_name=claims["name"],
            verified_email=True,  # Email verified by Entra ID
        )

    # Sync group memberships
    group_ids = claims["groups"]
    if claims["has_group_overage"]:
        # Token had too many groups — fetch from Graph API
        access_token = token_response.get("access_token", "")
        if access_token:
            group_ids = await fetch_user_groups_from_graph(access_token)

    if group_ids:
        await sync_team_memberships(user, group_ids)

    # Create session
    request.session["user"] = {"email": user.email}

    await audit_log(
        user=user, action="auth.login", resource_type="auth", details={"method": "entra_id"}, request=request
    )

    return RedirectResponse(url=state or "/", status_code=302)


@entra_router.get("/logout")
async def entra_logout(request: Request):
    """Logout from Entra ID and clear session."""
    from apollos.utils.entra import ENTRA_TENANT_ID

    request.session.pop("user", None)

    if ENTRA_TENANT_ID:
        # Redirect to Entra ID logout
        post_logout_uri = f"https://{request.base_url.hostname}/"
        return RedirectResponse(
            url=f"https://login.microsoftonline.com/{ENTRA_TENANT_ID}/oauth2/v2/logout"
            f"?post_logout_redirect_uri={post_logout_uri}",
            status_code=302,
        )

    return RedirectResponse(url="/", status_code=302)


@entra_router.get("/metadata")
async def entra_metadata(request: Request):
    """Return Entra ID OAuth metadata for frontend."""
    return {
        "entra": {
            "configured": is_entra_configured(),
            "login_url": "/auth/entra/login",
        }
    }
