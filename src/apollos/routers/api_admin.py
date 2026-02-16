"""Admin API endpoints for team/user/org management.

All endpoints require admin authentication (is_org_admin or is_staff).
"""

import json
import logging
from typing import Optional

from asgiref.sync import sync_to_async
from fastapi import APIRouter, Request
from pydantic import BaseModel
from starlette.authentication import requires
from starlette.responses import Response

from apollos.database.models import ApollosUser, Organization, Team, TeamMembership

logger = logging.getLogger(__name__)

api_admin = APIRouter()


# --- Request Bodies ---


class CreateTeamBody(BaseModel):
    name: str
    slug: str
    description: str = ""
    settings: dict = {}


class UpdateTeamBody(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    settings: Optional[dict] = None


class AddMemberBody(BaseModel):
    user_id: str  # UUID string
    role: str = "member"


class UpdateUserBody(BaseModel):
    is_org_admin: Optional[bool] = None


class UpdateOrgBody(BaseModel):
    name: Optional[str] = None
    settings: Optional[dict] = None


# --- Team Management ---


@api_admin.get("/teams")
@requires(["authenticated"])
async def list_teams(request: Request) -> Response:
    """List all teams in the organization."""
    from apollos.configure import require_admin

    require_admin(request)

    teams = await sync_to_async(list)(
        Team.objects.select_related("organization")
        .all()
        .values("id", "name", "slug", "description", "organization__name")
    )
    # Convert to serializable format
    team_list = []
    for t in teams:
        member_count = await TeamMembership.objects.filter(team_id=t["id"]).acount()
        team_list.append(
            {
                "id": t["id"],
                "name": t["name"],
                "slug": t["slug"],
                "description": t["description"],
                "organization": t["organization__name"],
                "member_count": member_count,
            }
        )

    return Response(content=json.dumps(team_list), media_type="application/json", status_code=200)


@api_admin.post("/teams")
@requires(["authenticated"])
async def create_team(request: Request, body: CreateTeamBody) -> Response:
    """Create a new team."""
    from apollos.configure import require_admin

    require_admin(request)

    # Get the first organization (single-org for now)
    org = await Organization.objects.afirst()
    if not org:
        return Response(
            content=json.dumps({"error": "No organization found. Create one first."}),
            media_type="application/json",
            status_code=400,
        )

    if await Team.objects.filter(slug=body.slug).aexists():
        return Response(
            content=json.dumps({"error": f"Team with slug '{body.slug}' already exists"}),
            media_type="application/json",
            status_code=409,
        )

    team = await Team.objects.acreate(
        name=body.name,
        slug=body.slug,
        description=body.description,
        organization=org,
        settings=body.settings,
    )

    return Response(
        content=json.dumps({"id": team.id, "name": team.name, "slug": team.slug}),
        media_type="application/json",
        status_code=201,
    )


@api_admin.put("/teams/{slug}")
@requires(["authenticated"])
async def update_team(request: Request, slug: str, body: UpdateTeamBody) -> Response:
    """Update an existing team."""
    from apollos.configure import require_admin

    require_admin(request)

    team = await Team.objects.filter(slug=slug).afirst()
    if not team:
        return Response(
            content=json.dumps({"error": "Team not found"}),
            media_type="application/json",
            status_code=404,
        )

    if body.name is not None:
        team.name = body.name
    if body.description is not None:
        team.description = body.description
    if body.settings is not None:
        team.settings = body.settings

    await sync_to_async(team.save)()

    return Response(
        content=json.dumps({"id": team.id, "name": team.name, "slug": team.slug}),
        media_type="application/json",
        status_code=200,
    )


@api_admin.delete("/teams/{slug}")
@requires(["authenticated"])
async def delete_team(request: Request, slug: str) -> Response:
    """Delete a team and all its memberships."""
    from apollos.configure import require_admin

    require_admin(request)

    team = await Team.objects.filter(slug=slug).afirst()
    if not team:
        return Response(
            content=json.dumps({"error": "Team not found"}),
            media_type="application/json",
            status_code=404,
        )

    await sync_to_async(team.delete)()

    return Response(
        content=json.dumps({"message": f"Team '{slug}' deleted"}),
        media_type="application/json",
        status_code=200,
    )


@api_admin.get("/teams/{slug}/members")
@requires(["authenticated"])
async def list_team_members(request: Request, slug: str) -> Response:
    """List all members of a team."""
    from apollos.configure import require_admin

    require_admin(request)

    team = await Team.objects.filter(slug=slug).afirst()
    if not team:
        return Response(
            content=json.dumps({"error": "Team not found"}),
            media_type="application/json",
            status_code=404,
        )

    members = await sync_to_async(list)(
        TeamMembership.objects.filter(team=team)
        .select_related("user")
        .values("user__uuid", "user__email", "user__username", "role")
    )
    member_list = [
        {
            "user_id": str(m["user__uuid"]),
            "email": m["user__email"],
            "username": m["user__username"],
            "role": m["role"],
        }
        for m in members
    ]

    return Response(content=json.dumps(member_list), media_type="application/json", status_code=200)


@api_admin.post("/teams/{slug}/members")
@requires(["authenticated"])
async def add_team_member(request: Request, slug: str, body: AddMemberBody) -> Response:
    """Add a user to a team."""
    from apollos.configure import require_admin

    require_admin(request)

    team = await Team.objects.filter(slug=slug).afirst()
    if not team:
        return Response(
            content=json.dumps({"error": "Team not found"}),
            media_type="application/json",
            status_code=404,
        )

    user = await ApollosUser.objects.filter(uuid=body.user_id).afirst()
    if not user:
        return Response(
            content=json.dumps({"error": "User not found"}),
            media_type="application/json",
            status_code=404,
        )

    if await TeamMembership.objects.filter(user=user, team=team).aexists():
        return Response(
            content=json.dumps({"error": "User is already a member of this team"}),
            media_type="application/json",
            status_code=409,
        )

    valid_roles = [r.value for r in TeamMembership.Role]
    if body.role not in valid_roles:
        return Response(
            content=json.dumps({"error": f"Invalid role. Must be one of: {valid_roles}"}),
            media_type="application/json",
            status_code=400,
        )

    membership = await TeamMembership.objects.acreate(user=user, team=team, role=body.role)

    return Response(
        content=json.dumps({"user_id": str(user.uuid), "team_slug": team.slug, "role": membership.role}),
        media_type="application/json",
        status_code=201,
    )


@api_admin.delete("/teams/{slug}/members/{user_uuid}")
@requires(["authenticated"])
async def remove_team_member(request: Request, slug: str, user_uuid: str) -> Response:
    """Remove a user from a team."""
    from apollos.configure import require_admin

    require_admin(request)

    team = await Team.objects.filter(slug=slug).afirst()
    if not team:
        return Response(
            content=json.dumps({"error": "Team not found"}),
            media_type="application/json",
            status_code=404,
        )

    membership = await TeamMembership.objects.filter(user__uuid=user_uuid, team=team).afirst()
    if not membership:
        return Response(
            content=json.dumps({"error": "User is not a member of this team"}),
            media_type="application/json",
            status_code=404,
        )

    await sync_to_async(membership.delete)()

    return Response(
        content=json.dumps({"message": f"User removed from team '{slug}'"}),
        media_type="application/json",
        status_code=200,
    )


# --- User Management ---


@api_admin.get("/users")
@requires(["authenticated"])
async def list_users(request: Request) -> Response:
    """List all users."""
    from apollos.configure import require_admin

    require_admin(request)

    users = await sync_to_async(list)(
        ApollosUser.objects.all().values("uuid", "email", "username", "is_org_admin", "is_active", "is_staff")
    )
    user_list = [
        {
            "user_id": str(u["uuid"]),
            "email": u["email"],
            "username": u["username"],
            "is_org_admin": u["is_org_admin"],
            "is_active": u["is_active"],
            "is_staff": u["is_staff"],
        }
        for u in users
    ]

    return Response(content=json.dumps(user_list), media_type="application/json", status_code=200)


@api_admin.put("/users/{user_uuid}")
@requires(["authenticated"])
async def update_user(request: Request, user_uuid: str, body: UpdateUserBody) -> Response:
    """Update user admin status."""
    from apollos.configure import require_admin

    require_admin(request)

    target_user = await ApollosUser.objects.filter(uuid=user_uuid).afirst()
    if not target_user:
        return Response(
            content=json.dumps({"error": "User not found"}),
            media_type="application/json",
            status_code=404,
        )

    if body.is_org_admin is not None:
        target_user.is_org_admin = body.is_org_admin
        await sync_to_async(target_user.save)(update_fields=["is_org_admin"])

    return Response(
        content=json.dumps(
            {
                "user_id": str(target_user.uuid),
                "email": target_user.email,
                "is_org_admin": target_user.is_org_admin,
            }
        ),
        media_type="application/json",
        status_code=200,
    )


# --- Organization Settings ---


@api_admin.get("/org")
@requires(["authenticated"])
async def get_org_settings(request: Request) -> Response:
    """Get organization settings."""
    from apollos.configure import require_admin

    require_admin(request)

    org = await Organization.objects.afirst()
    if not org:
        return Response(
            content=json.dumps({"error": "No organization found"}),
            media_type="application/json",
            status_code=404,
        )

    return Response(
        content=json.dumps({"name": org.name, "slug": org.slug, "settings": org.settings}),
        media_type="application/json",
        status_code=200,
    )


@api_admin.put("/org")
@requires(["authenticated"])
async def update_org_settings(request: Request, body: UpdateOrgBody) -> Response:
    """Update organization settings."""
    from apollos.configure import require_admin

    require_admin(request)

    org = await Organization.objects.afirst()
    if not org:
        return Response(
            content=json.dumps({"error": "No organization found"}),
            media_type="application/json",
            status_code=404,
        )

    if body.name is not None:
        org.name = body.name
    if body.settings is not None:
        org.settings = body.settings

    await sync_to_async(org.save)()

    return Response(
        content=json.dumps({"name": org.name, "slug": org.slug, "settings": org.settings}),
        media_type="application/json",
        status_code=200,
    )
