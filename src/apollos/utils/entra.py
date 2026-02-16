"""Microsoft Entra ID (Azure AD) OIDC integration via MSAL."""

import logging
import os

import httpx
import msal

logger = logging.getLogger(__name__)

# Entra ID configuration from environment
ENTRA_TENANT_ID = os.environ.get("APOLLOS_ENTRA_TENANT_ID", "")
ENTRA_CLIENT_ID = os.environ.get("APOLLOS_ENTRA_CLIENT_ID", "")
ENTRA_CLIENT_SECRET = os.environ.get("APOLLOS_ENTRA_CLIENT_SECRET", "")
ENTRA_REDIRECT_URI = os.environ.get("APOLLOS_ENTRA_REDIRECT_URI", "")
ENTRA_AUTHORITY = f"https://login.microsoftonline.com/{ENTRA_TENANT_ID}" if ENTRA_TENANT_ID else ""
ENTRA_SCOPES = ["User.Read"]  # Basic profile + email


def is_entra_configured() -> bool:
    """Check if Entra ID SSO is configured."""
    return bool(ENTRA_TENANT_ID and ENTRA_CLIENT_ID and ENTRA_CLIENT_SECRET)


def get_msal_app() -> msal.ConfidentialClientApplication:
    """Create MSAL confidential client application."""
    if not is_entra_configured():
        raise ValueError("Entra ID not configured. Set APOLLOS_ENTRA_* environment variables.")
    return msal.ConfidentialClientApplication(
        ENTRA_CLIENT_ID,
        authority=ENTRA_AUTHORITY,
        client_credential=ENTRA_CLIENT_SECRET,
    )


def get_auth_url(msal_app: msal.ConfidentialClientApplication, state: str = "") -> str:
    """Get authorization URL for Entra ID login.

    Returns the authorization URL string.
    """
    return msal_app.get_authorization_request_url(
        scopes=ENTRA_SCOPES,
        redirect_uri=ENTRA_REDIRECT_URI,
        state=state,
        prompt="select_account",
    )


def acquire_token_by_code(msal_app: msal.ConfidentialClientApplication, code: str) -> dict:
    """Exchange authorization code for tokens.

    Returns MSAL token response dict with 'id_token_claims', 'access_token', etc.
    """
    return msal_app.acquire_token_by_authorization_code(
        code,
        scopes=ENTRA_SCOPES,
        redirect_uri=ENTRA_REDIRECT_URI,
    )


def extract_user_claims(token_response: dict) -> dict:
    """Extract user info from MSAL token response.

    Uses 'oid' as primary identifier (stable across app registrations).
    Falls back to 'sub' only if 'oid' is missing.
    """
    claims = token_response.get("id_token_claims", {})
    return {
        "oid": claims.get("oid") or claims.get("sub"),
        "email": claims.get("preferred_username") or claims.get("email", ""),
        "name": claims.get("name", ""),
        "given_name": claims.get("given_name", ""),
        "family_name": claims.get("family_name", ""),
        "upn": claims.get("upn") or claims.get("preferred_username", ""),
        "groups": claims.get("groups", []),
        "has_group_overage": "_claim_names" in claims and "groups" in claims.get("_claim_names", {}),
    }


async def fetch_user_groups_from_graph(access_token: str) -> list[str]:
    """Fetch user's group memberships from Microsoft Graph API.

    Used when group overage occurs (user in >200 groups).
    """
    groups = []
    url = "https://graph.microsoft.com/v1.0/me/memberOf?$select=id,displayName,groupTypes"
    headers = {"Authorization": f"Bearer {access_token}"}

    async with httpx.AsyncClient() as client:
        while url:
            resp = await client.get(url, headers=headers)
            if resp.status_code != 200:
                logger.error(f"Graph API error: {resp.status_code} {resp.text}")
                break
            data = resp.json()
            for member in data.get("value", []):
                if member.get("@odata.type") == "#microsoft.graph.group":
                    groups.append(member["id"])
            url = data.get("@odata.nextLink")

    return groups


async def sync_team_memberships(user, entra_group_ids: list[str]):
    """Sync user's team memberships based on Entra ID group claims.

    - Adds memberships for Entra groups that map to local Teams
    - Removes memberships for Teams the user is no longer in (via Entra)
    - Does NOT remove memberships for Teams without entra_group_id (manually assigned)
    """
    from asgiref.sync import sync_to_async
    from django.utils import timezone

    from apollos.database.models import Team, TeamMembership

    # Get teams that have Entra group mappings
    mapped_teams = await sync_to_async(list)(Team.objects.filter(entra_group_id__in=entra_group_ids))
    mapped_team_ids = {t.id for t in mapped_teams}

    # Get user's current Entra-mapped team memberships (exclude empty string mappings)
    current_memberships = await sync_to_async(list)(
        TeamMembership.objects.filter(user=user, team__entra_group_id__isnull=False).exclude(team__entra_group_id="")
    )
    current_team_ids = {m.team_id for m in current_memberships}

    # Add new memberships
    teams_to_add = mapped_team_ids - current_team_ids
    for team in mapped_teams:
        if team.id in teams_to_add:
            await TeamMembership.objects.acreate(user=user, team=team, role=TeamMembership.Role.MEMBER)

    # Remove stale Entra-mapped memberships (user left group in Entra)
    teams_to_remove = current_team_ids - mapped_team_ids
    if teams_to_remove:
        await sync_to_async(TeamMembership.objects.filter(user=user, team_id__in=teams_to_remove).delete)()

    # Update sync timestamp
    user.last_synced_at = timezone.now()
    await user.asave(update_fields=["last_synced_at"])
