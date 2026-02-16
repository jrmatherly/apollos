import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from apollos.configure import configure_middleware, configure_routes
from apollos.database.models import ApollosApiUser, Entry
from apollos.utils import state
from tests.helpers import OrganizationFactory, TeamFactory, TeamMembershipFactory, UserFactory

DUMMY_EMBEDDINGS = [0.1] * 384


def _make_client():
    """Create a minimal test client with routes configured."""
    state.anonymous_mode = False
    app = FastAPI()
    configure_routes(app)
    configure_middleware(app)
    return TestClient(app)


def _create_entry(user, file_path="test.md", visibility="private", team=None):
    return Entry.objects.create(
        user=user,
        visibility=visibility,
        team=team,
        raw="test content",
        compiled="test content",
        heading="test",
        file_path=file_path,
        file_source="computer",
        file_type="markdown",
        corpus_id=str(user.uuid),
        hashed_value=f"hash-{user.pk}-{file_path}",
        embeddings=DUMMY_EMBEDDINGS,
    )


def _auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.django_db(transaction=True)
class TestShareContent:
    """Integration tests for POST /api/content/share."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.org = OrganizationFactory()
        self.team_a = TeamFactory(organization=self.org)
        self.team_b = TeamFactory(organization=self.org)

        self.user = UserFactory()
        self.admin = UserFactory()
        self.admin.is_org_admin = True
        self.admin.save()

        TeamMembershipFactory(user=self.user, team=self.team_a)
        # user is NOT a member of team_b
        TeamMembershipFactory(user=self.admin, team=self.team_a)
        TeamMembershipFactory(user=self.admin, team=self.team_b)

        # Create API tokens
        self.user_api = ApollosApiUser.objects.create(user=self.user, name="user-key", token="test-user-token")
        self.admin_api = ApollosApiUser.objects.create(user=self.admin, name="admin-key", token="test-admin-token")

        self.client = _make_client()

    def test_share_to_own_team(self):
        """User shares file to team_a (member) -- 200, entries updated."""
        _create_entry(self.user, file_path="share-own-team.md")

        response = self.client.post(
            "/api/content/share",
            json={"file_path": "share-own-team.md", "visibility": "team", "team_slug": self.team_a.slug},
            headers=_auth_headers(self.user_api.token),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "shared"
        assert data["count"] == 1
        assert data["visibility"] == "team"

        entry = Entry.objects.get(user=self.user, file_path="share-own-team.md")
        assert entry.visibility == "team"
        assert entry.team == self.team_a

    def test_share_to_non_member_team_denied(self):
        """User shares to team_b (not member) -- 403."""
        _create_entry(self.user, file_path="share-non-member.md")

        response = self.client.post(
            "/api/content/share",
            json={"file_path": "share-non-member.md", "visibility": "team", "team_slug": self.team_b.slug},
            headers=_auth_headers(self.user_api.token),
        )

        assert response.status_code == 403

    def test_admin_share_to_any_team(self):
        """Admin shares to team_b -- 200."""
        _create_entry(self.admin, file_path="admin-share-team.md")

        response = self.client.post(
            "/api/content/share",
            json={"file_path": "admin-share-team.md", "visibility": "team", "team_slug": self.team_b.slug},
            headers=_auth_headers(self.admin_api.token),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "shared"
        assert data["count"] == 1

        entry = Entry.objects.get(user=self.admin, file_path="admin-share-team.md")
        assert entry.visibility == "team"
        assert entry.team == self.team_b

    def test_admin_share_org_wide(self):
        """Admin shares with visibility='org' -- 200."""
        _create_entry(self.admin, file_path="admin-share-org.md")

        response = self.client.post(
            "/api/content/share",
            json={"file_path": "admin-share-org.md", "visibility": "org"},
            headers=_auth_headers(self.admin_api.token),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "shared"
        assert data["count"] == 1
        assert data["visibility"] == "org"

        entry = Entry.objects.get(user=self.admin, file_path="admin-share-org.md")
        assert entry.visibility == "org"

    def test_non_admin_org_share_denied(self):
        """Non-admin user shares with visibility='org' -- 403."""
        _create_entry(self.user, file_path="user-org-share.md")

        response = self.client.post(
            "/api/content/share",
            json={"file_path": "user-org-share.md", "visibility": "org"},
            headers=_auth_headers(self.user_api.token),
        )

        assert response.status_code == 403

    def test_missing_file_path_returns_400(self):
        """No file_path in body -- 400."""
        response = self.client.post(
            "/api/content/share",
            json={"visibility": "team", "team_slug": self.team_a.slug},
            headers=_auth_headers(self.user_api.token),
        )

        assert response.status_code == 400

    def test_missing_visibility_returns_400(self):
        """No visibility in body -- 400."""
        response = self.client.post(
            "/api/content/share",
            json={"file_path": "something.md"},
            headers=_auth_headers(self.user_api.token),
        )

        assert response.status_code == 400

    def test_invalid_visibility_returns_400(self):
        """visibility='invalid' -- 400."""
        response = self.client.post(
            "/api/content/share",
            json={"file_path": "something.md", "visibility": "invalid"},
            headers=_auth_headers(self.user_api.token),
        )

        assert response.status_code == 400

    def test_no_entries_returns_404(self):
        """Share a file_path that has no entries -- 404."""
        response = self.client.post(
            "/api/content/share",
            json={
                "file_path": "nonexistent-file.md",
                "visibility": "team",
                "team_slug": self.team_a.slug,
            },
            headers=_auth_headers(self.user_api.token),
        )

        assert response.status_code == 404

    def test_shared_by_field_set(self):
        """After sharing, verify entry.shared_by == user."""
        _create_entry(self.user, file_path="shared-by-check.md")

        response = self.client.post(
            "/api/content/share",
            json={"file_path": "shared-by-check.md", "visibility": "team", "team_slug": self.team_a.slug},
            headers=_auth_headers(self.user_api.token),
        )

        assert response.status_code == 200

        entry = Entry.objects.get(user=self.user, file_path="shared-by-check.md")
        assert entry.shared_by == self.user
