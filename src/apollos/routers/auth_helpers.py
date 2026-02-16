"""Role-based access control utilities for FastAPI endpoints.

Usage patterns:
    # Admin-only endpoint
    @requires(["authenticated"])
    def my_endpoint(request):
        require_admin(request)  # Raises 403 if not admin

    # Team lead for specific team
    @requires(["authenticated"])
    def my_endpoint(request, team_slug: str):
        require_team_role(request, team_slug, min_role="team_lead")

    # Any team member
    @requires(["authenticated"])
    def my_endpoint(request, team_slug: str):
        require_team_role(request, team_slug, min_role="member")
"""

import logging

from fastapi import HTTPException, Request

from apollos.database.models import ApollosUser, Team, TeamMembership

logger = logging.getLogger(__name__)

# Role hierarchy (higher index = more permissions)
ROLE_HIERARCHY = {
    "member": 0,
    "team_lead": 1,
    "admin": 2,
}


def require_admin(request: Request) -> ApollosUser:
    """Check that the authenticated user is an org admin.

    Re-exports from configure.py for convenience. Checks is_org_admin OR is_staff.
    Raises HTTPException(401) if not authenticated, HTTPException(403) if not admin.
    """
    from apollos.configure import require_admin as _require_admin

    return _require_admin(request)


def get_user_role_in_team(user: ApollosUser, team: Team) -> str | None:
    """Get user's role in a specific team, or None if not a member."""
    membership = TeamMembership.objects.filter(user=user, team=team).first()
    return membership.role if membership else None


async def aget_user_role_in_team(user: ApollosUser, team: Team) -> str | None:
    """Async version of get_user_role_in_team."""
    from asgiref.sync import sync_to_async

    return await sync_to_async(get_user_role_in_team)(user, team)


def require_team_role(request: Request, team_slug: str, min_role: str = "member") -> tuple[ApollosUser, Team]:
    """Verify user has at least the specified role in the given team.

    Args:
        request: The HTTP request
        team_slug: The team's slug
        min_role: Minimum required role ("member", "team_lead", or "admin")

    Returns:
        Tuple of (user, team)

    Raises:
        HTTPException(401): Not authenticated
        HTTPException(403): Insufficient permissions
        HTTPException(404): Team not found
    """
    if not request.user.is_authenticated:
        raise HTTPException(status_code=401, detail="Authentication required")

    user = request.user.object

    # Org admins bypass team role checks
    if user.is_org_admin or user.is_staff:
        team = Team.objects.filter(slug=team_slug).first()
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")
        return user, team

    team = Team.objects.filter(slug=team_slug).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    role = get_user_role_in_team(user, team)
    if role is None:
        raise HTTPException(status_code=403, detail="Not a member of this team")

    min_level = ROLE_HIERARCHY.get(min_role, 0)
    user_level = ROLE_HIERARCHY.get(role, 0)

    if user_level < min_level:
        raise HTTPException(status_code=403, detail=f"Requires {min_role} role or higher")

    return user, team


async def arequire_team_role(request: Request, team_slug: str, min_role: str = "member") -> tuple[ApollosUser, Team]:
    """Async version of require_team_role."""
    from asgiref.sync import sync_to_async

    return await sync_to_async(require_team_role)(request, team_slug, min_role)


def get_user_highest_role(user: ApollosUser) -> str:
    """Get user's highest role across all teams.

    Returns 'admin' if is_org_admin, otherwise highest team role, or 'member' as default.
    """
    if user.is_org_admin or user.is_staff:
        return "admin"

    memberships = TeamMembership.objects.filter(user=user)
    highest = "member"
    for m in memberships:
        if ROLE_HIERARCHY.get(m.role, 0) > ROLE_HIERARCHY.get(highest, 0):
            highest = m.role
    return highest


def get_user_teams(user: ApollosUser) -> list[dict]:
    """Get all teams the user belongs to with their roles."""
    memberships = TeamMembership.objects.filter(user=user).select_related("team")
    return [
        {
            "team_slug": m.team.slug,
            "team_name": m.team.name,
            "role": m.role,
        }
        for m in memberships
    ]
