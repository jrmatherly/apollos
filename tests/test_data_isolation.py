import pytest
from django.db.models import Q

from apollos.database.adapters import (
    AgentAdapters,
    build_entry_access_filter,
    get_user_team_ids,
)
from apollos.database.models import Agent, Entry, UserMemory
from tests.helpers import ChatModelFactory, OrganizationFactory, TeamFactory, TeamMembershipFactory, UserFactory

# Dummy embeddings vector (384 dimensions to match thenlper/gte-small default)
DUMMY_EMBEDDINGS = [0.1] * 384


def _create_entry(user, visibility, team=None, raw="test content"):
    """Helper to create an Entry with required fields including embeddings."""
    return Entry.objects.create(
        user=user,
        visibility=visibility,
        team=team,
        raw=raw,
        compiled=raw,
        heading="test",
        file_path="test.md",
        file_source="computer",
        file_type="markdown",
        corpus_id=str(user.uuid),
        hashed_value=f"hash-{user.pk}-{raw[:10]}",
        embeddings=DUMMY_EMBEDDINGS,
    )


@pytest.mark.django_db
class TestGetUserTeamIds:
    """Tests for the get_user_team_ids helper function."""

    def test_single_team_member(self):
        org = OrganizationFactory()
        team = TeamFactory(organization=org)
        user = UserFactory()
        TeamMembershipFactory(user=user, team=team)

        result = get_user_team_ids(user)
        assert set(result) == {team.id}

    def test_multi_team_member(self):
        org = OrganizationFactory()
        team_a = TeamFactory(organization=org)
        team_b = TeamFactory(organization=org)
        user = UserFactory()
        TeamMembershipFactory(user=user, team=team_a)
        TeamMembershipFactory(user=user, team=team_b)

        result = get_user_team_ids(user)
        assert set(result) == {team_a.id, team_b.id}

    def test_no_team_member(self):
        user = UserFactory()
        assert get_user_team_ids(user) == []

    def test_none_user(self):
        assert get_user_team_ids(None) == []


@pytest.mark.django_db
class TestBuildEntryAccessFilter:
    """Tests for build_entry_access_filter and Entry visibility tiers."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Create users, org, teams for all entry access tests."""
        self.org = OrganizationFactory()
        self.team_a = TeamFactory(organization=self.org)
        self.team_b = TeamFactory(organization=self.org)

        self.user_a = UserFactory()  # Member of team_a
        self.user_b = UserFactory()  # Member of team_b
        self.user_c = UserFactory()  # Member of both teams
        self.outsider = UserFactory()  # No team membership

        TeamMembershipFactory(user=self.user_a, team=self.team_a)
        TeamMembershipFactory(user=self.user_b, team=self.team_b)
        TeamMembershipFactory(user=self.user_c, team=self.team_a)
        TeamMembershipFactory(user=self.user_c, team=self.team_b)

    def test_none_user_none_agent_returns_empty(self):
        """No user and no agent should return an empty Q filter."""
        assert build_entry_access_filter(None, None) == Q(pk__in=[])

    def test_private_entry_only_visible_to_owner(self):
        """Private entry should only be accessible to the owning user."""
        entry = _create_entry(self.user_a, Entry.Visibility.PRIVATE, raw="private content")

        # Owner can see it
        owner_filter = build_entry_access_filter(self.user_a)
        assert Entry.objects.filter(owner_filter).filter(pk=entry.pk).exists()

        # Other team member cannot
        other_filter = build_entry_access_filter(self.user_b)
        assert not Entry.objects.filter(other_filter).filter(pk=entry.pk).exists()

        # Multi-team user cannot see someone else's private entry
        multi_filter = build_entry_access_filter(self.user_c)
        assert not Entry.objects.filter(multi_filter).filter(pk=entry.pk).exists()

        # Outsider cannot
        outsider_filter = build_entry_access_filter(self.outsider)
        assert not Entry.objects.filter(outsider_filter).filter(pk=entry.pk).exists()

    def test_team_entry_visible_to_team_members_only(self):
        """Team-visible entry should be accessible to members of that team only."""
        entry = _create_entry(self.user_a, Entry.Visibility.TEAM, team=self.team_a, raw="team content")

        # Team A member (owner) can see it
        member_filter = build_entry_access_filter(self.user_a)
        assert Entry.objects.filter(member_filter).filter(pk=entry.pk).exists()

        # User C (both teams, including team_a) can see it
        multi_filter = build_entry_access_filter(self.user_c)
        assert Entry.objects.filter(multi_filter).filter(pk=entry.pk).exists()

        # Team B only member cannot see team_a entry
        other_filter = build_entry_access_filter(self.user_b)
        assert not Entry.objects.filter(other_filter).filter(pk=entry.pk).exists()

        # Outsider cannot
        outsider_filter = build_entry_access_filter(self.outsider)
        assert not Entry.objects.filter(outsider_filter).filter(pk=entry.pk).exists()

    def test_org_entry_visible_to_all_authenticated(self):
        """Organization-wide entry should be visible to all authenticated users."""
        entry = _create_entry(self.user_a, Entry.Visibility.ORGANIZATION, raw="org content")

        for user in [self.user_a, self.user_b, self.user_c, self.outsider]:
            user_filter = build_entry_access_filter(user)
            assert Entry.objects.filter(user_filter).filter(pk=entry.pk).exists(), (
                f"{user.username} should see org-wide entry"
            )

    def test_team_entry_requires_team_field(self):
        """Creating a team-visible entry without a team should raise ValidationError."""
        from django.core.exceptions import ValidationError

        with pytest.raises(ValidationError, match="Team-visible entries must have a team assigned"):
            _create_entry(self.user_a, Entry.Visibility.TEAM, team=None, raw="invalid team entry")

    def test_mixed_visibility_entries_filtered_correctly(self):
        """User should see only the entries their access level permits."""
        private_a = _create_entry(self.user_a, Entry.Visibility.PRIVATE, raw="private A")
        private_b = _create_entry(self.user_b, Entry.Visibility.PRIVATE, raw="private B")
        team_a_entry = _create_entry(self.user_a, Entry.Visibility.TEAM, team=self.team_a, raw="team A entry")
        team_b_entry = _create_entry(self.user_b, Entry.Visibility.TEAM, team=self.team_b, raw="team B entry")
        org_entry = _create_entry(self.user_a, Entry.Visibility.ORGANIZATION, raw="org entry")

        # user_a: should see private_a, team_a_entry, org_entry (NOT private_b, NOT team_b_entry)
        user_a_filter = build_entry_access_filter(self.user_a)
        user_a_entries = set(Entry.objects.filter(user_a_filter).values_list("pk", flat=True))
        assert private_a.pk in user_a_entries
        assert team_a_entry.pk in user_a_entries
        assert org_entry.pk in user_a_entries
        assert private_b.pk not in user_a_entries
        assert team_b_entry.pk not in user_a_entries

        # user_c (both teams): should see team_a_entry, team_b_entry, org_entry (NOT private_a, NOT private_b)
        user_c_filter = build_entry_access_filter(self.user_c)
        user_c_entries = set(Entry.objects.filter(user_c_filter).values_list("pk", flat=True))
        assert team_a_entry.pk in user_c_entries
        assert team_b_entry.pk in user_c_entries
        assert org_entry.pk in user_c_entries
        assert private_a.pk not in user_c_entries
        assert private_b.pk not in user_c_entries

        # outsider: should see only org_entry
        outsider_filter = build_entry_access_filter(self.outsider)
        outsider_entries = set(Entry.objects.filter(outsider_filter).values_list("pk", flat=True))
        assert org_entry.pk in outsider_entries
        assert private_a.pk not in outsider_entries
        assert team_a_entry.pk not in outsider_entries

    def test_agent_owned_entries_bypass_visibility(self):
        """Agent-owned entries should be accessible when agent is passed to filter."""
        chat_model = ChatModelFactory()
        agent = Agent.objects.create(
            name="KB Agent for entry test",
            slug="kb-agent-entry-test",
            chat_model=chat_model,
            creator=self.user_a,
        )
        # Agent entry: no user, just agent
        agent_entry = Entry.objects.create(
            agent=agent,
            visibility=Entry.Visibility.PRIVATE,
            raw="agent KB content",
            compiled="agent KB content",
            heading="agent heading",
            file_path="agent.md",
            file_source="computer",
            file_type="markdown",
            hashed_value="hash-agent-entry",
            embeddings=DUMMY_EMBEDDINGS,
        )

        # Without agent param, user_b cannot see it
        user_filter = build_entry_access_filter(self.user_b)
        assert not Entry.objects.filter(user_filter).filter(pk=agent_entry.pk).exists()

        # With agent param, entries are accessible
        agent_filter = build_entry_access_filter(None, agent=agent)
        assert Entry.objects.filter(agent_filter).filter(pk=agent_entry.pk).exists()


@pytest.mark.django_db
class TestAgentVisibility:
    """Tests for Agent privacy levels and get_all_accessible_agents."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Create users, org, teams, and a shared chat model."""
        self.org = OrganizationFactory()
        self.team_a = TeamFactory(organization=self.org)
        self.team_b = TeamFactory(organization=self.org)

        self.user_a = UserFactory()
        self.user_b = UserFactory()
        self.user_c = UserFactory()
        self.outsider = UserFactory()

        TeamMembershipFactory(user=self.user_a, team=self.team_a)
        TeamMembershipFactory(user=self.user_b, team=self.team_b)
        TeamMembershipFactory(user=self.user_c, team=self.team_a)
        TeamMembershipFactory(user=self.user_c, team=self.team_b)

        self.chat_model = ChatModelFactory()

    def test_private_agent_visible_only_to_creator(self):
        """Agent with PRIVATE privacy should only be visible to its creator."""
        agent = Agent.objects.create(
            name="Private Agent Isolation",
            slug="private-agent-isolation",
            privacy_level=Agent.PrivacyLevel.PRIVATE,
            creator=self.user_a,
            chat_model=self.chat_model,
        )
        accessible_a = list(AgentAdapters.get_all_accessible_agents(self.user_a))
        assert agent in accessible_a

        accessible_b = list(AgentAdapters.get_all_accessible_agents(self.user_b))
        assert agent not in accessible_b

        accessible_outsider = list(AgentAdapters.get_all_accessible_agents(self.outsider))
        assert agent not in accessible_outsider

    def test_team_agent_visible_to_team_members_only(self):
        """Agent with TEAM privacy should be visible to team members, not outsiders."""
        agent = Agent.objects.create(
            name="Team Agent Isolation",
            slug="team-agent-isolation",
            privacy_level=Agent.PrivacyLevel.TEAM,
            team=self.team_a,
            creator=self.user_a,
            chat_model=self.chat_model,
        )
        # Team A member sees it
        accessible_a = list(AgentAdapters.get_all_accessible_agents(self.user_a))
        assert agent in accessible_a

        # User C (member of both teams, including team_a) sees it
        accessible_c = list(AgentAdapters.get_all_accessible_agents(self.user_c))
        assert agent in accessible_c

        # Team B only member does NOT see it
        accessible_b = list(AgentAdapters.get_all_accessible_agents(self.user_b))
        assert agent not in accessible_b

        # Outsider does NOT see it
        accessible_outsider = list(AgentAdapters.get_all_accessible_agents(self.outsider))
        assert agent not in accessible_outsider

    def test_org_agent_visible_to_all_authenticated(self):
        """Agent with ORGANIZATION privacy should be visible to all authenticated users."""
        agent = Agent.objects.create(
            name="Org Agent Isolation",
            slug="org-agent-isolation",
            privacy_level=Agent.PrivacyLevel.ORGANIZATION,
            creator=self.user_a,
            chat_model=self.chat_model,
        )
        for user in [self.user_a, self.user_b, self.user_c, self.outsider]:
            accessible = list(AgentAdapters.get_all_accessible_agents(user))
            assert agent in accessible, f"{user.username} should see org-level agent"

    def test_unauthenticated_sees_only_admin_org_agents(self):
        """Unauthenticated (None user) should only see admin-managed org agents."""
        # Non-admin org agent
        user_org_agent = Agent.objects.create(
            name="User Org Agent Isolation",
            slug="user-org-agent-isolation",
            privacy_level=Agent.PrivacyLevel.ORGANIZATION,
            creator=self.user_a,
            chat_model=self.chat_model,
        )
        # Admin-managed org agent (creator=None triggers managed_by_admin=True)
        admin_org_agent = Agent.objects.create(
            name="Admin Org Agent Isolation",
            slug="admin-org-agent-isolation",
            privacy_level=Agent.PrivacyLevel.ORGANIZATION,
            creator=None,
            chat_model=self.chat_model,
        )

        accessible = list(AgentAdapters.get_all_accessible_agents(None))
        # Admin-managed org agent should be visible
        assert admin_org_agent in accessible
        # User-created org agent should NOT be visible to unauthenticated
        assert user_org_agent not in accessible


@pytest.mark.django_db
class TestUserMemoryIsolation:
    """Tests for UserMemory privacy -- always per-user."""

    def test_user_memory_never_visible_to_others(self):
        """UserMemory should always be private per user (simple ORM filter)."""
        user_a = UserFactory()
        user_b = UserFactory()

        memory = UserMemory.objects.create(
            user=user_a,
            raw="important thing to remember",
            embeddings=DUMMY_EMBEDDINGS,
        )

        # Owner can see it
        own_memories = UserMemory.objects.filter(user=user_a)
        assert memory in own_memories

        # Other user cannot
        other_memories = UserMemory.objects.filter(user=user_b)
        assert memory not in other_memories

    def test_user_memory_isolated_across_team_members(self):
        """UserMemory should not leak across team members."""
        org = OrganizationFactory()
        team = TeamFactory(organization=org)
        user_a = UserFactory()
        user_b = UserFactory()
        TeamMembershipFactory(user=user_a, team=team)
        TeamMembershipFactory(user=user_b, team=team)

        memory_a = UserMemory.objects.create(
            user=user_a,
            raw="user A secret memory",
            embeddings=DUMMY_EMBEDDINGS,
        )
        memory_b = UserMemory.objects.create(
            user=user_b,
            raw="user B secret memory",
            embeddings=DUMMY_EMBEDDINGS,
        )

        # user_a only sees their own
        a_memories = set(UserMemory.objects.filter(user=user_a).values_list("pk", flat=True))
        assert memory_a.pk in a_memories
        assert memory_b.pk not in a_memories

        # user_b only sees their own
        b_memories = set(UserMemory.objects.filter(user=user_b).values_list("pk", flat=True))
        assert memory_b.pk in b_memories
        assert memory_a.pk not in b_memories
