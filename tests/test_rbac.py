"""Tests for Role-Based Access Control (RBAC) enforcement.

Tests the permission matrix:
- Admin: full access
- Team Lead: manage own team's content/agents
- Member: personal content/agents only
- Non-member: no team access
"""

import json
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from apollos.database.models import (
    ApollosUser,
    Team,
    TeamMembership,
)
from apollos.routers.auth_helpers import (
    ROLE_HIERARCHY,
    get_user_highest_role,
    get_user_role_in_team,
    get_user_teams,
    require_admin,
    require_team_role,
)
from tests.helpers import (
    OrganizationFactory,
    TeamFactory,
    TeamMembershipFactory,
    UserFactory,
)

# ---------------------------------------------------------------------------
# Unit Tests for auth_helpers
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestRoleHierarchy:
    """Verify the numeric ordering of the ROLE_HIERARCHY constant."""

    def test_member_is_lowest(self):
        assert ROLE_HIERARCHY["member"] < ROLE_HIERARCHY["team_lead"]
        assert ROLE_HIERARCHY["member"] < ROLE_HIERARCHY["admin"]

    def test_team_lead_is_middle(self):
        assert ROLE_HIERARCHY["team_lead"] > ROLE_HIERARCHY["member"]
        assert ROLE_HIERARCHY["team_lead"] < ROLE_HIERARCHY["admin"]

    def test_admin_is_highest(self):
        assert ROLE_HIERARCHY["admin"] > ROLE_HIERARCHY["team_lead"]
        assert ROLE_HIERARCHY["admin"] > ROLE_HIERARCHY["member"]

    def test_hierarchy_has_three_roles(self):
        assert set(ROLE_HIERARCHY.keys()) == {"member", "team_lead", "admin"}


@pytest.mark.django_db
class TestGetUserRoleInTeam:
    """Test get_user_role_in_team returns correct role or None."""

    def test_returns_role_for_member(self):
        membership = TeamMembershipFactory(role=TeamMembership.Role.MEMBER)
        assert get_user_role_in_team(membership.user, membership.team) == "member"

    def test_returns_role_for_team_lead(self):
        membership = TeamMembershipFactory(role=TeamMembership.Role.TEAM_LEAD)
        assert get_user_role_in_team(membership.user, membership.team) == "team_lead"

    def test_returns_role_for_admin(self):
        membership = TeamMembershipFactory(role=TeamMembership.Role.ADMIN)
        assert get_user_role_in_team(membership.user, membership.team) == "admin"

    def test_returns_none_for_non_member(self):
        user = UserFactory()
        team = TeamFactory()
        assert get_user_role_in_team(user, team) is None

    def test_returns_none_for_different_team(self):
        """User in team A should get None for team B."""
        membership = TeamMembershipFactory(role=TeamMembership.Role.MEMBER)
        other_team = TeamFactory()
        assert get_user_role_in_team(membership.user, other_team) is None


@pytest.mark.django_db
class TestGetUserHighestRole:
    """Test get_user_highest_role picks the maximum across all memberships."""

    def test_org_admin_returns_admin(self):
        user = UserFactory(is_org_admin=True)
        assert get_user_highest_role(user) == "admin"

    def test_staff_returns_admin(self):
        user = UserFactory(is_staff=True)
        assert get_user_highest_role(user) == "admin"

    def test_org_admin_overrides_lower_membership(self):
        """is_org_admin should return admin even if only a member of a team."""
        user = UserFactory(is_org_admin=True)
        TeamMembershipFactory(user=user, role=TeamMembership.Role.MEMBER)
        assert get_user_highest_role(user) == "admin"

    def test_team_lead_returns_team_lead(self):
        membership = TeamMembershipFactory(role=TeamMembership.Role.TEAM_LEAD)
        assert get_user_highest_role(membership.user) == "team_lead"

    def test_member_returns_member(self):
        membership = TeamMembershipFactory(role=TeamMembership.Role.MEMBER)
        assert get_user_highest_role(membership.user) == "member"

    def test_highest_across_teams(self):
        """When user has multiple memberships, return the highest role."""
        user = UserFactory()
        org = OrganizationFactory()
        team1 = TeamFactory(organization=org)
        team2 = TeamFactory(organization=org)
        TeamMembershipFactory(user=user, team=team1, role=TeamMembership.Role.MEMBER)
        TeamMembershipFactory(user=user, team=team2, role=TeamMembership.Role.TEAM_LEAD)
        assert get_user_highest_role(user) == "team_lead"

    def test_no_memberships_returns_member(self):
        user = UserFactory()
        assert get_user_highest_role(user) == "member"

    def test_admin_membership_returns_admin(self):
        """A team-level admin membership (not is_org_admin) should return admin."""
        membership = TeamMembershipFactory(role=TeamMembership.Role.ADMIN)
        assert get_user_highest_role(membership.user) == "admin"


@pytest.mark.django_db
class TestGetUserTeams:
    """Test get_user_teams returns team info with roles."""

    def test_returns_all_teams(self):
        user = UserFactory()
        org = OrganizationFactory()
        team1 = TeamFactory(organization=org, name="Team A")
        team2 = TeamFactory(organization=org, name="Team B")
        TeamMembershipFactory(user=user, team=team1, role=TeamMembership.Role.MEMBER)
        TeamMembershipFactory(user=user, team=team2, role=TeamMembership.Role.TEAM_LEAD)
        teams = get_user_teams(user)
        assert len(teams) == 2
        slugs = {t["team_slug"] for t in teams}
        assert team1.slug in slugs
        assert team2.slug in slugs

    def test_returns_empty_for_no_teams(self):
        user = UserFactory()
        assert get_user_teams(user) == []

    def test_includes_role_info(self):
        membership = TeamMembershipFactory(role=TeamMembership.Role.TEAM_LEAD)
        teams = get_user_teams(membership.user)
        assert len(teams) == 1
        assert teams[0]["role"] == "team_lead"
        assert teams[0]["team_name"] == membership.team.name

    def test_includes_team_slug(self):
        membership = TeamMembershipFactory()
        teams = get_user_teams(membership.user)
        assert teams[0]["team_slug"] == membership.team.slug

    def test_does_not_include_other_users_teams(self):
        """User should not see teams they are not a member of."""
        user = UserFactory()
        other_membership = TeamMembershipFactory()  # Different user
        TeamMembershipFactory(user=user)
        teams = get_user_teams(user)
        assert len(teams) == 1
        assert teams[0]["team_slug"] != other_membership.team.slug


# ---------------------------------------------------------------------------
# Unit Tests for require_admin
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestRequireAdmin:
    """Test require_admin raises for non-admins and passes for admins."""

    def _make_request(self, user=None, authenticated=True):
        """Build a mock request with user.object set to the given user."""
        request = MagicMock()
        if authenticated and user:
            request.user.is_authenticated = True
            request.user.object = user
        else:
            request.user.is_authenticated = False
        return request

    def test_unauthenticated_raises_401(self):
        request = self._make_request(authenticated=False)
        with pytest.raises(HTTPException) as exc_info:
            require_admin(request)
        assert exc_info.value.status_code == 401

    def test_non_admin_raises_403(self):
        user = UserFactory(is_org_admin=False, is_staff=False)
        request = self._make_request(user)
        with pytest.raises(HTTPException) as exc_info:
            require_admin(request)
        assert exc_info.value.status_code == 403

    def test_org_admin_passes(self):
        user = UserFactory(is_org_admin=True)
        request = self._make_request(user)
        result = require_admin(request)
        assert result == user

    def test_staff_passes(self):
        user = UserFactory(is_staff=True)
        request = self._make_request(user)
        result = require_admin(request)
        assert result == user


# ---------------------------------------------------------------------------
# Unit Tests for require_team_role
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestRequireTeamRole:
    """Test require_team_role enforces role hierarchy on team access."""

    def _make_request(self, user=None, authenticated=True):
        request = MagicMock()
        if authenticated and user:
            request.user.is_authenticated = True
            request.user.object = user
        else:
            request.user.is_authenticated = False
        return request

    def test_unauthenticated_raises_401(self):
        request = self._make_request(authenticated=False)
        with pytest.raises(HTTPException) as exc_info:
            require_team_role(request, "some-team", "member")
        assert exc_info.value.status_code == 401

    def test_non_member_raises_403(self):
        user = UserFactory()
        team = TeamFactory()
        request = self._make_request(user)
        with pytest.raises(HTTPException) as exc_info:
            require_team_role(request, team.slug, "member")
        assert exc_info.value.status_code == 403

    def test_nonexistent_team_raises_404(self):
        user = UserFactory()
        request = self._make_request(user)
        with pytest.raises(HTTPException) as exc_info:
            require_team_role(request, "nonexistent-slug", "member")
        assert exc_info.value.status_code == 404

    def test_member_passes_member_check(self):
        membership = TeamMembershipFactory(role=TeamMembership.Role.MEMBER)
        request = self._make_request(membership.user)
        user, team = require_team_role(request, membership.team.slug, "member")
        assert user == membership.user
        assert team == membership.team

    def test_member_fails_team_lead_check(self):
        membership = TeamMembershipFactory(role=TeamMembership.Role.MEMBER)
        request = self._make_request(membership.user)
        with pytest.raises(HTTPException) as exc_info:
            require_team_role(request, membership.team.slug, "team_lead")
        assert exc_info.value.status_code == 403

    def test_member_fails_admin_check(self):
        membership = TeamMembershipFactory(role=TeamMembership.Role.MEMBER)
        request = self._make_request(membership.user)
        with pytest.raises(HTTPException) as exc_info:
            require_team_role(request, membership.team.slug, "admin")
        assert exc_info.value.status_code == 403

    def test_team_lead_passes_member_check(self):
        membership = TeamMembershipFactory(role=TeamMembership.Role.TEAM_LEAD)
        request = self._make_request(membership.user)
        user, team = require_team_role(request, membership.team.slug, "member")
        assert user == membership.user

    def test_team_lead_passes_team_lead_check(self):
        membership = TeamMembershipFactory(role=TeamMembership.Role.TEAM_LEAD)
        request = self._make_request(membership.user)
        user, team = require_team_role(request, membership.team.slug, "team_lead")
        assert user == membership.user

    def test_team_lead_fails_admin_check(self):
        membership = TeamMembershipFactory(role=TeamMembership.Role.TEAM_LEAD)
        request = self._make_request(membership.user)
        with pytest.raises(HTTPException) as exc_info:
            require_team_role(request, membership.team.slug, "admin")
        assert exc_info.value.status_code == 403

    def test_team_admin_passes_all_checks(self):
        membership = TeamMembershipFactory(role=TeamMembership.Role.ADMIN)
        request = self._make_request(membership.user)
        for role in ["member", "team_lead", "admin"]:
            user, team = require_team_role(request, membership.team.slug, role)
            assert user == membership.user

    def test_org_admin_bypasses_team_membership(self):
        """Org admins can access any team even without membership."""
        user = UserFactory(is_org_admin=True)
        team = TeamFactory()
        request = self._make_request(user)
        result_user, result_team = require_team_role(request, team.slug, "admin")
        assert result_user == user
        assert result_team == team

    def test_staff_bypasses_team_membership(self):
        """Staff users can access any team even without membership."""
        user = UserFactory(is_staff=True)
        team = TeamFactory()
        request = self._make_request(user)
        result_user, result_team = require_team_role(request, team.slug, "admin")
        assert result_user == user
        assert result_team == team

    def test_org_admin_still_needs_valid_team(self):
        """Org admin bypasses role check but team must exist."""
        user = UserFactory(is_org_admin=True)
        request = self._make_request(user)
        with pytest.raises(HTTPException) as exc_info:
            require_team_role(request, "nonexistent-slug", "member")
        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# API Integration Tests — Admin Endpoint Access
# ---------------------------------------------------------------------------

# The `client` fixture creates a FastAPI TestClient backed by an api_user
# with token "kk-secret". That user is NOT an admin by default.

AUTH_HEADERS = {"Authorization": "Bearer kk-secret"}


@pytest.mark.django_db(transaction=True)
class TestUserProfileEndpoint:
    """Test GET /api/v1/user returns role information."""

    def test_profile_includes_role_fields(self, client):
        response = client.get("/api/v1/user", headers=AUTH_HEADERS)
        assert response.status_code == 200
        data = response.json()
        assert "is_org_admin" in data
        assert "highest_role" in data
        assert "teams" in data

    def test_non_admin_has_correct_defaults(self, client):
        response = client.get("/api/v1/user", headers=AUTH_HEADERS)
        data = response.json()
        assert data["is_org_admin"] is False
        assert data["highest_role"] == "member"
        assert data["teams"] == []

    def test_admin_profile(self, client):
        # Get the authenticated user and make them admin
        response = client.get("/api/v1/user", headers=AUTH_HEADERS)
        data = response.json()
        user = ApollosUser.objects.get(username=data["username"])
        user.is_org_admin = True
        user.save()

        response = client.get("/api/v1/user", headers=AUTH_HEADERS)
        data = response.json()
        assert data["is_org_admin"] is True
        assert data["highest_role"] == "admin"

    def test_team_member_profile(self, client):
        """Profile should list teams the user belongs to."""
        response = client.get("/api/v1/user", headers=AUTH_HEADERS)
        data = response.json()
        user = ApollosUser.objects.get(username=data["username"])

        org = OrganizationFactory()
        team = TeamFactory(organization=org, name="Engineering")
        TeamMembership.objects.create(user=user, team=team, role=TeamMembership.Role.TEAM_LEAD)

        response = client.get("/api/v1/user", headers=AUTH_HEADERS)
        data = response.json()
        assert data["highest_role"] == "team_lead"
        assert len(data["teams"]) == 1
        assert data["teams"][0]["team_slug"] == team.slug
        assert data["teams"][0]["role"] == "team_lead"


@pytest.mark.django_db(transaction=True)
class TestAdminEndpointAccess:
    """Test that admin endpoints require admin role.

    All /api/admin/* endpoints call require_admin(request) which raises 403
    for non-admin users. The `client` fixture provides a non-admin user.
    """

    def test_non_admin_cannot_list_teams(self, client):
        response = client.get("/api/admin/teams", headers=AUTH_HEADERS)
        assert response.status_code == 403

    def test_non_admin_cannot_create_team(self, client):
        response = client.post(
            "/api/admin/teams",
            content=json.dumps({"name": "Test", "slug": "test"}),
            headers={**AUTH_HEADERS, "Content-Type": "application/json"},
        )
        assert response.status_code == 403

    def test_non_admin_cannot_update_team(self, client):
        team = TeamFactory()
        response = client.put(
            f"/api/admin/teams/{team.slug}",
            content=json.dumps({"name": "New Name"}),
            headers={**AUTH_HEADERS, "Content-Type": "application/json"},
        )
        assert response.status_code == 403

    def test_non_admin_cannot_delete_team(self, client):
        team = TeamFactory()
        response = client.delete(f"/api/admin/teams/{team.slug}", headers=AUTH_HEADERS)
        assert response.status_code == 403

    def test_non_admin_cannot_list_team_members(self, client):
        team = TeamFactory()
        response = client.get(f"/api/admin/teams/{team.slug}/members", headers=AUTH_HEADERS)
        assert response.status_code == 403

    def test_non_admin_cannot_add_team_member(self, client):
        team = TeamFactory()
        user = UserFactory()
        response = client.post(
            f"/api/admin/teams/{team.slug}/members",
            content=json.dumps({"user_id": str(user.uuid), "role": "member"}),
            headers={**AUTH_HEADERS, "Content-Type": "application/json"},
        )
        assert response.status_code == 403

    def test_non_admin_cannot_remove_team_member(self, client):
        membership = TeamMembershipFactory()
        response = client.delete(
            f"/api/admin/teams/{membership.team.slug}/members/{membership.user.uuid}",
            headers=AUTH_HEADERS,
        )
        assert response.status_code == 403

    def test_non_admin_cannot_list_users(self, client):
        response = client.get("/api/admin/users", headers=AUTH_HEADERS)
        assert response.status_code == 403

    def test_non_admin_cannot_update_user(self, client):
        target = UserFactory()
        response = client.put(
            f"/api/admin/users/{target.uuid}",
            content=json.dumps({"is_org_admin": True}),
            headers={**AUTH_HEADERS, "Content-Type": "application/json"},
        )
        assert response.status_code == 403

    def test_non_admin_cannot_get_org(self, client):
        response = client.get("/api/admin/org", headers=AUTH_HEADERS)
        assert response.status_code == 403

    def test_non_admin_cannot_update_org(self, client):
        response = client.put(
            "/api/admin/org",
            content=json.dumps({"name": "New Org Name"}),
            headers={**AUTH_HEADERS, "Content-Type": "application/json"},
        )
        assert response.status_code == 403

    def test_unauthenticated_cannot_access_admin(self, client):
        """Without any auth header, admin endpoints should reject the request."""
        response = client.get("/api/admin/teams")
        # Starlette's @requires(["authenticated"]) returns 403 for unauthenticated requests
        assert response.status_code == 403


@pytest.mark.django_db(transaction=True)
class TestAdminEndpointAccessGranted:
    """Test that admin endpoints work for admin users.

    Elevates the authenticated test user to org admin and verifies access.
    """

    def _make_admin(self, client):
        """Promote the client's authenticated user to org admin."""
        response = client.get("/api/v1/user", headers=AUTH_HEADERS)
        data = response.json()
        user = ApollosUser.objects.get(username=data["username"])
        user.is_org_admin = True
        user.save()
        return user

    def test_admin_can_list_teams(self, client):
        self._make_admin(client)
        response = client.get("/api/admin/teams", headers=AUTH_HEADERS)
        assert response.status_code == 200

    def test_admin_can_create_team(self, client):
        self._make_admin(client)
        # Need an organization first
        OrganizationFactory()
        response = client.post(
            "/api/admin/teams",
            content=json.dumps({"name": "New Team", "slug": "new-team"}),
            headers={**AUTH_HEADERS, "Content-Type": "application/json"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Team"
        assert data["slug"] == "new-team"

    def test_admin_can_list_users(self, client):
        self._make_admin(client)
        response = client.get("/api/admin/users", headers=AUTH_HEADERS)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1  # At least the admin user itself

    def test_admin_can_get_org(self, client):
        self._make_admin(client)
        org = OrganizationFactory()
        response = client.get("/api/admin/org", headers=AUTH_HEADERS)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == org.name

    def test_admin_can_manage_team_members(self, client):
        self._make_admin(client)
        org = OrganizationFactory()
        team = TeamFactory(organization=org)
        target_user = UserFactory()

        # Add member
        response = client.post(
            f"/api/admin/teams/{team.slug}/members",
            content=json.dumps({"user_id": str(target_user.uuid), "role": "member"}),
            headers={**AUTH_HEADERS, "Content-Type": "application/json"},
        )
        assert response.status_code == 201

        # List members
        response = client.get(f"/api/admin/teams/{team.slug}/members", headers=AUTH_HEADERS)
        assert response.status_code == 200
        members = response.json()
        assert any(m["user_id"] == str(target_user.uuid) for m in members)

        # Remove member
        response = client.delete(
            f"/api/admin/teams/{team.slug}/members/{target_user.uuid}",
            headers=AUTH_HEADERS,
        )
        assert response.status_code == 200

    def test_admin_can_delete_team(self, client):
        self._make_admin(client)
        org = OrganizationFactory()
        team = TeamFactory(organization=org)
        slug = team.slug

        response = client.delete(f"/api/admin/teams/{slug}", headers=AUTH_HEADERS)
        assert response.status_code == 200
        assert not Team.objects.filter(slug=slug).exists()

    def test_admin_can_update_user(self, client):
        self._make_admin(client)
        target = UserFactory()
        response = client.put(
            f"/api/admin/users/{target.uuid}",
            content=json.dumps({"is_org_admin": True}),
            headers={**AUTH_HEADERS, "Content-Type": "application/json"},
        )
        assert response.status_code == 200
        target.refresh_from_db()
        assert target.is_org_admin is True
