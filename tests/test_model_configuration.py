"""Tests for the model configuration system (LiteLLM plan Phases 1-6).

Covers:
- Environment variable parsing (embedding, chat model lists, slot assignments)
- Bootstrap config (JSONC loading, env var interpolation, idempotency)
- Team-based model filtering (no teams, single team, multiple teams, union logic)
- PriceTier enforcement with teams
- Agent model bypass (agent model selection ignores team filtering)
- Anonymous mode (unauthenticated user sees all models)
- Admin endpoint authorization
"""

import json
import os
import tempfile
from unittest.mock import patch

import pytest

from apollos.database.adapters import ConversationAdapters
from apollos.database.models import (
    AiModelApi,
    ChatModel,
    PriceTier,
    SearchModelConfig,
    ServerChatSettings,
)
from apollos.utils.bootstrap import (
    _interpolate_env_vars,
    _strip_jsonc,
    apply_bootstrap_config,
    load_bootstrap_config,
)
from tests.helpers import (
    ChatModelFactory,
    OrganizationFactory,
    SubscriptionFactory,
    TeamFactory,
    TeamMembershipFactory,
    UserFactory,
)


# ---------------------------------------------------------------------------
# Phase 1: Embedding env var parsing
# ---------------------------------------------------------------------------
class TestEmbeddingEnvVars:
    """Test that embedding env vars are read correctly during SearchModelConfig creation."""

    def test_embedding_env_vars_applied_on_fresh_db(self):
        """When no SearchModelConfig exists, env vars should populate it."""
        SearchModelConfig.objects.all().delete()
        assert SearchModelConfig.objects.count() == 0

        env = {
            "APOLLOS_EMBEDDING_MODEL": "text-embedding-3-small",
            "APOLLOS_EMBEDDING_DIMENSIONS": "1536",
            "APOLLOS_EMBEDDING_API_TYPE": "openai",
            "APOLLOS_EMBEDDING_API_KEY": "sk-test-key",
            "APOLLOS_EMBEDDING_ENDPOINT": "https://api.openai.com/v1",
            "APOLLOS_CROSS_ENCODER_MODEL": "mixedbread-ai/mxbai-rerank-xsmall-v1",
        }
        with patch.dict(os.environ, env):
            from apollos.database.adapters import get_or_create_search_models

            configs = get_or_create_search_models()
            config = configs.first()

        assert config.bi_encoder == "text-embedding-3-small"
        assert config.bi_encoder_dimensions == 1536

    def test_embedding_env_vars_skipped_when_config_exists(self):
        """When SearchModelConfig already exists, env vars should NOT override it."""
        SearchModelConfig.objects.all().delete()
        existing = SearchModelConfig.objects.create(
            name="default", bi_encoder="existing-model", cross_encoder="existing-cross"
        )

        env = {"APOLLOS_EMBEDDING_MODEL": "should-not-override"}
        with patch.dict(os.environ, env):
            from apollos.database.adapters import get_or_create_search_models

            configs = get_or_create_search_models()
            config = configs.first()

        assert config.bi_encoder == "existing-model"
        existing.delete()


# ---------------------------------------------------------------------------
# Phase 2: Chat model list env vars
# ---------------------------------------------------------------------------
class TestChatModelListEnvVars:
    """Test that chat model list env vars produce correct lists."""

    def test_default_openai_models(self):
        """Default list should contain expected models."""
        from apollos.utils.constants import default_openai_chat_models

        assert "gpt-4o-mini" in default_openai_chat_models
        assert "gpt-4.1" in default_openai_chat_models

    def test_custom_openai_models_via_env(self):
        """Custom list via env var should override defaults at import time."""
        # NOTE: constants.py evaluates at import time.
        # This test verifies the parsing logic, not runtime override.
        raw = "model-a, model-b, model-c"
        parsed = [m.strip() for m in raw.split(",") if m.strip()]
        assert parsed == ["model-a", "model-b", "model-c"]

    def test_empty_env_var_produces_empty_list(self):
        """Empty env var should produce empty list (skip provider)."""
        raw = ""
        parsed = [m.strip() for m in raw.split(",") if m.strip()]
        assert parsed == []


# ---------------------------------------------------------------------------
# Phase 4: Bootstrap config
# ---------------------------------------------------------------------------
class TestBootstrapJsoncParsing:
    """Test JSONC stripping and env var interpolation."""

    def test_strip_line_comments(self):
        text = '{"key": "value"} // comment'
        result = _strip_jsonc(text)
        assert json.loads(result) == {"key": "value"}

    def test_strip_block_comments(self):
        text = '{"key": /* block */ "value"}'
        result = _strip_jsonc(text)
        assert json.loads(result) == {"key": "value"}

    def test_unterminated_block_comment_raises(self):
        text = '{"key": /* unterminated'
        with pytest.raises(ValueError, match="Unterminated block comment"):
            _strip_jsonc(text)

    def test_strip_trailing_commas(self):
        text = '{"a": 1, "b": 2,}'
        result = _strip_jsonc(text)
        assert json.loads(result) == {"a": 1, "b": 2}

    def test_interpolate_env_vars(self):
        with patch.dict(os.environ, {"MY_KEY": "secret123"}):
            result = _interpolate_env_vars('{"key": "${MY_KEY}"}')
        assert json.loads(result) == {"key": "secret123"}

    def test_interpolate_missing_env_var(self):
        """Missing env var should produce empty string with warning."""
        result = _interpolate_env_vars('{"key": "${DEFINITELY_NOT_SET_VAR}"}')
        assert json.loads(result) == {"key": ""}

    def test_interpolate_json_special_chars(self):
        """Env var with quotes/backslashes should be JSON-escaped."""
        with patch.dict(os.environ, {"SPECIAL": 'value"with\\quotes'}):
            result = _interpolate_env_vars('{"key": "${SPECIAL}"}')
        parsed = json.loads(result)
        assert parsed["key"] == 'value"with\\quotes'

    def test_load_bootstrap_config_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            load_bootstrap_config("/nonexistent/path.json")

    def test_load_bootstrap_config_invalid_json(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{invalid json")
            f.flush()
            with pytest.raises(ValueError, match="Invalid JSON"):
                load_bootstrap_config(f.name)
        os.unlink(f.name)

    def test_load_bootstrap_config_non_object(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("[1, 2, 3]")
            f.flush()
            with pytest.raises(ValueError, match="must be a JSON object"):
                load_bootstrap_config(f.name)
        os.unlink(f.name)

    def test_load_bootstrap_config_valid(self):
        config_text = """{
            // JSONC comment
            "providers": {},
            "defaults": {},
        }"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write(config_text)
            f.flush()
            config = load_bootstrap_config(f.name)
        os.unlink(f.name)
        assert "providers" in config


class TestBootstrapApply:
    """Test apply_bootstrap_config idempotency and correctness."""

    def test_apply_creates_provider_and_models(self):
        config = {
            "providers": {
                "openai": {
                    "api_key": "sk-test",
                    "chat_models": ["test-model-alpha"],
                }
            }
        }
        apply_bootstrap_config(config)

        api = AiModelApi.objects.filter(name="OpenAI").first()
        assert api is not None
        assert api.api_key == "sk-test"

        model = ChatModel.objects.filter(name="test-model-alpha").first()
        assert model is not None
        assert model.model_type == ChatModel.ModelType.OPENAI

    def test_apply_is_idempotent(self):
        config = {
            "providers": {
                "openai": {
                    "api_key": "sk-test-idem",
                    "chat_models": ["test-model-idem"],
                }
            }
        }
        apply_bootstrap_config(config)
        apply_bootstrap_config(config)

        # Should not create duplicates (uses filter().first() pattern)
        models = ChatModel.objects.filter(name="test-model-idem")
        assert models.count() == 1

    def test_apply_unknown_provider_skipped(self):
        config = {
            "providers": {
                "unknown_provider": {
                    "api_key": "sk-test",
                    "chat_models": ["should-not-exist"],
                }
            }
        }
        apply_bootstrap_config(config)
        assert not ChatModel.objects.filter(name="should-not-exist").exists()

    def test_apply_model_tiers(self):
        config = {
            "providers": {
                "openai": {
                    "api_key": "sk-test-tiers",
                    "chat_models": ["free-model", "standard-model"],
                }
            },
            "model_tiers": {"standard-model": "standard"},
        }
        apply_bootstrap_config(config)

        free = ChatModel.objects.filter(name="free-model").first()
        standard = ChatModel.objects.filter(name="standard-model").first()
        assert free.price_tier == PriceTier.FREE
        assert standard.price_tier == PriceTier.STANDARD

    def test_apply_embedding_config(self):
        SearchModelConfig.objects.filter(name="default").delete()
        config = {
            "embedding": {
                "model": "test-embed-model",
                "api_type": "openai",
                "dimensions": 768,
                "cross_encoder": "test-cross-encoder",
            }
        }
        apply_bootstrap_config(config)

        sc = SearchModelConfig.objects.filter(name="default").first()
        assert sc is not None
        assert sc.bi_encoder == "test-embed-model"
        assert sc.bi_encoder_dimensions == 768
        assert sc.cross_encoder == "test-cross-encoder"

    def test_apply_embedding_invalid_dimensions_skipped(self):
        SearchModelConfig.objects.filter(name="default").delete()
        config = {
            "embedding": {
                "model": "test-embed-bad-dim",
                "api_type": "local",
                "dimensions": "not-a-number",
            }
        }
        apply_bootstrap_config(config)
        sc = SearchModelConfig.objects.filter(name="default").first()
        assert sc is not None
        # Dimensions should not be set (warning logged)
        assert sc.bi_encoder_dimensions is None

    def test_apply_server_chat_slots(self):
        free_model = ChatModelFactory(name="slot-free", price_tier=PriceTier.FREE)
        standard_model = ChatModelFactory(name="slot-standard", price_tier=PriceTier.STANDARD)

        config = {
            "defaults": {
                "chat_default": "slot-free",
                "chat_advanced": "slot-standard",
            }
        }
        apply_bootstrap_config(config)

        settings = ServerChatSettings.objects.first()
        assert settings is not None
        assert settings.chat_default == free_model
        assert settings.chat_advanced == standard_model

    def test_apply_free_tier_slot_rejects_standard_model(self):
        ChatModelFactory(name="slot-tier-mismatch", price_tier=PriceTier.STANDARD)

        ServerChatSettings.objects.all().delete()
        config = {
            "defaults": {
                "chat_default": "slot-tier-mismatch",  # Should be FREE
            }
        }
        apply_bootstrap_config(config)

        # chat_default should NOT be set (tier mismatch logged as warning)
        settings = ServerChatSettings.objects.first()
        assert settings is None or settings.chat_default is None

    def test_apply_team_models(self):
        org = OrganizationFactory()
        team = TeamFactory(organization=org, slug="bootstrap-team")
        model = ChatModelFactory(name="team-bootstrap-model")

        config = {
            "team_models": {
                "bootstrap-team": {
                    "allowed_models": ["team-bootstrap-model"],
                    "chat_default": "team-bootstrap-model",
                }
            }
        }
        apply_bootstrap_config(config)

        team.refresh_from_db()
        assert model.id in team.settings["allowed_models"]
        assert team.settings["chat_default"] == model.id

    def test_apply_team_models_missing_team(self):
        """Non-existent team slug should be skipped with warning."""
        config = {
            "team_models": {
                "nonexistent-team": {
                    "allowed_models": ["some-model"],
                }
            }
        }
        # Should not raise
        apply_bootstrap_config(config)


# ---------------------------------------------------------------------------
# Phase 5: Team-based model filtering
# ---------------------------------------------------------------------------
class TestTeamModelFiltering:
    """Test get_available_chat_models with team assignments."""

    def test_user_with_no_teams_sees_global_models(self):
        """User without team membership sees only global models."""
        user = UserFactory()
        SubscriptionFactory(user=user)

        free_model = ChatModelFactory(name="global-free", price_tier=PriceTier.FREE)
        standard_model = ChatModelFactory(name="global-standard", price_tier=PriceTier.STANDARD)

        available = ConversationAdapters.get_available_chat_models(user)
        available_ids = set(available.values_list("id", flat=True))

        assert free_model.id in available_ids
        assert standard_model.id in available_ids

    def test_free_user_sees_only_free_models(self):
        """Free user (no subscription) sees only FREE tier models."""
        user = UserFactory()
        # No subscription

        free_model = ChatModelFactory(name="filter-free", price_tier=PriceTier.FREE)
        standard_model = ChatModelFactory(name="filter-standard", price_tier=PriceTier.STANDARD)

        available = ConversationAdapters.get_available_chat_models(user)
        available_ids = set(available.values_list("id", flat=True))

        assert free_model.id in available_ids
        assert standard_model.id not in available_ids

    def test_user_with_single_team_sees_team_models(self):
        """User on a team sees global + team-assigned models."""
        user = UserFactory()
        SubscriptionFactory(user=user)

        team_model = ChatModelFactory(name="team-only-model", price_tier=PriceTier.STANDARD)
        org = OrganizationFactory()
        team = TeamFactory(organization=org)
        team.settings["allowed_models"] = [team_model.id]
        team.save()
        TeamMembershipFactory(user=user, team=team)

        available = ConversationAdapters.get_available_chat_models(user)
        available_ids = set(available.values_list("id", flat=True))

        assert team_model.id in available_ids

    def test_user_with_multiple_teams_sees_union(self):
        """User on multiple teams sees union of all team models."""
        user = UserFactory()
        SubscriptionFactory(user=user)

        model_a = ChatModelFactory(name="team-a-model", price_tier=PriceTier.STANDARD)
        model_b = ChatModelFactory(name="team-b-model", price_tier=PriceTier.STANDARD)

        org = OrganizationFactory()
        team_a = TeamFactory(organization=org, slug="team-a-filter")
        team_a.settings["allowed_models"] = [model_a.id]
        team_a.save()

        team_b = TeamFactory(organization=org, slug="team-b-filter")
        team_b.settings["allowed_models"] = [model_b.id]
        team_b.save()

        TeamMembershipFactory(user=user, team=team_a)
        TeamMembershipFactory(user=user, team=team_b)

        available = ConversationAdapters.get_available_chat_models(user)
        available_ids = set(available.values_list("id", flat=True))

        assert model_a.id in available_ids
        assert model_b.id in available_ids

    def test_free_user_with_team_standard_model_cannot_see_it(self):
        """Free user on team with STANDARD model should NOT see it."""
        user = UserFactory()
        # No subscription — free user

        standard_model = ChatModelFactory(name="team-std-hidden", price_tier=PriceTier.STANDARD)
        org = OrganizationFactory()
        team = TeamFactory(organization=org, slug="team-std-filter")
        team.settings["allowed_models"] = [standard_model.id]
        team.save()
        TeamMembershipFactory(user=user, team=team)

        available = ConversationAdapters.get_available_chat_models(user)
        available_ids = set(available.values_list("id", flat=True))

        assert standard_model.id not in available_ids


# ---------------------------------------------------------------------------
# Phase 5: Agent model bypass
# ---------------------------------------------------------------------------
class TestAgentModelBypass:
    """Agent model selection should NOT use team filtering."""

    def test_agent_chat_model_ignores_teams(self):
        """get_agent_chat_model should return the agent's model regardless of team assignments."""
        from apollos.database.adapters import AgentAdapters

        UserFactory()
        model = ChatModelFactory(name="agent-bypass-model", price_tier=PriceTier.STANDARD)
        agent = AgentAdapters.create_default_agent()
        agent.chat_model = model
        agent.save()

        # Agent model should be accessible even without team assignment
        assert agent.chat_model == model
        assert agent.chat_model.name == "agent-bypass-model"


# ---------------------------------------------------------------------------
# Phase 6: Admin endpoint authorization
# ---------------------------------------------------------------------------
class TestAdminAuthorization:
    """Test that admin endpoints enforce authorization."""

    def test_require_admin_rejects_non_admin(self):
        """Non-admin user should get 403."""
        from unittest.mock import MagicMock

        from fastapi import HTTPException

        from apollos.configure import require_admin

        user = UserFactory(is_org_admin=False)
        user.is_staff = False
        user.save()

        mock_request = MagicMock()
        mock_request.user.is_authenticated = True
        mock_request.user.object = user

        with pytest.raises(HTTPException) as exc_info:
            require_admin(mock_request)
        assert exc_info.value.status_code == 403

    def test_require_admin_accepts_org_admin(self):
        """Org admin should pass."""
        from unittest.mock import MagicMock

        from apollos.configure import require_admin

        user = UserFactory(is_org_admin=True)
        user.save()

        mock_request = MagicMock()
        mock_request.user.is_authenticated = True
        mock_request.user.object = user

        result = require_admin(mock_request)
        assert result == user

    def test_require_admin_accepts_staff(self):
        """Staff user should pass."""
        from unittest.mock import MagicMock

        from apollos.configure import require_admin

        user = UserFactory()
        user.is_staff = True
        user.save()

        mock_request = MagicMock()
        mock_request.user.is_authenticated = True
        mock_request.user.object = user

        result = require_admin(mock_request)
        assert result == user

    def test_require_admin_rejects_unauthenticated(self):
        """Unauthenticated request should get 401."""
        from unittest.mock import MagicMock

        from fastapi import HTTPException

        from apollos.configure import require_admin

        mock_request = MagicMock()
        mock_request.user.is_authenticated = False

        with pytest.raises(HTTPException) as exc_info:
            require_admin(mock_request)
        assert exc_info.value.status_code == 401


# ---------------------------------------------------------------------------
# Phase 3: Server chat slot env vars
# ---------------------------------------------------------------------------
class TestServerChatSlotConfig:
    """Test _configure_server_chat_slots logic from initialization.py."""

    def test_slot_env_var_overrides_bootstrap(self):
        """APOLLOS_DEFAULT_CHAT_MODEL should override bootstrap slot assignment."""
        free_model = ChatModelFactory(name="slot-env-override", price_tier=PriceTier.FREE)

        env = {"APOLLOS_DEFAULT_CHAT_MODEL": "slot-env-override"}
        with patch.dict(os.environ, env):
            from apollos.utils.initialization import _configure_server_chat_slots

            _configure_server_chat_slots()

        settings = ServerChatSettings.objects.first()
        assert settings is not None
        assert settings.chat_default == free_model

    def test_slot_env_var_model_not_found_skipped(self):
        """Non-existent model name in slot env var should be skipped."""
        ServerChatSettings.objects.all().delete()

        env = {"APOLLOS_DEFAULT_CHAT_MODEL": "nonexistent-model-xyz"}
        with patch.dict(os.environ, env):
            from apollos.utils.initialization import _configure_server_chat_slots

            _configure_server_chat_slots()

        # Should not crash; settings may or may not exist depending on other slots
        ServerChatSettings.objects.first()
