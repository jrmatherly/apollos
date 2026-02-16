"""Bootstrap configuration for Apollos model setup.

Loads a JSONC configuration file and idempotently creates/updates providers,
chat models, embedding config, and server chat slot assignments.

Usage:
    config = load_bootstrap_config("/path/to/bootstrap.jsonc")
    apply_bootstrap_config(config)
"""

import json
import logging
import os
import re

logger = logging.getLogger(__name__)


def _strip_jsonc(text: str) -> str:
    """Strip // and /* */ comments and trailing commas from JSONC text."""
    result = []
    i = 0
    in_string = False
    while i < len(text):
        ch = text[i]
        if in_string:
            result.append(ch)
            if ch == "\\" and i + 1 < len(text):
                result.append(text[i + 1])
                i += 2
                continue
            if ch == '"':
                in_string = False
            i += 1
            continue
        if ch == '"':
            in_string = True
            result.append(ch)
            i += 1
            continue
        if ch == "/" and i + 1 < len(text):
            if text[i + 1] == "/":
                while i < len(text) and text[i] != "\n":
                    i += 1
                continue
            if text[i + 1] == "*":
                comment_start = i
                i += 2
                while i + 1 < len(text) and not (text[i] == "*" and text[i + 1] == "/"):
                    i += 1
                if i + 1 >= len(text):
                    raise ValueError(f"Unterminated block comment starting at position {comment_start}")
                i += 2
                continue
        result.append(ch)
        i += 1
    cleaned = "".join(result)
    # Remove trailing commas before } or ]
    cleaned = re.sub(r",\s*([}\]])", r"\1", cleaned)
    return cleaned


def _interpolate_env_vars(text: str) -> str:
    """Replace ${VAR_NAME} patterns with environment variable values.

    Values are JSON-escaped so that special characters (quotes, backslashes)
    don't break the JSON structure when substituted inside string literals.
    """

    def replacer(match):
        var_name = match.group(1)
        value = os.getenv(var_name)
        if value is None:
            logger.warning(f"Bootstrap config: env var ${{{var_name}}} not set, using empty string.")
            return ""
        # JSON-escape the value to prevent breaking JSON string boundaries.
        # json.dumps adds surrounding quotes; strip them to get just the escaped content.
        return json.dumps(value)[1:-1]

    return re.sub(r"\$\{([^}]+)\}", replacer, text)


def load_bootstrap_config(path: str) -> dict:
    """Load and parse a JSONC bootstrap configuration file.

    Strips comments, interpolates ${ENV_VAR} references, and parses as JSON.
    Raises on file not found or invalid JSON.
    """
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Bootstrap config file not found: {path}")

    with open(path) as f:
        raw = f.read()

    stripped = _strip_jsonc(raw)
    interpolated = _interpolate_env_vars(stripped)

    try:
        config = json.loads(interpolated)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in bootstrap config {path}: {e}") from e

    if not isinstance(config, dict):
        raise ValueError(f"Bootstrap config must be a JSON object, got {type(config).__name__}")

    return config


def apply_bootstrap_config(config: dict):
    """Idempotently apply bootstrap configuration.

    Creates/updates providers, chat models, embedding config, and server chat slots.
    Safe to call multiple times — uses update_or_create for all records.
    """
    # Lazy imports to avoid circular imports and ensure Django is initialized
    from apollos.database.models import (
        AiModelApi,
        ChatModel,
        PriceTier,
        SearchModelConfig,
        ServerChatSettings,
    )
    from apollos.processor.conversation.utils import model_to_prompt_size, model_to_tokenizer

    provider_meta = {
        "openai": {"model_type": ChatModel.ModelType.OPENAI, "name": "OpenAI"},
        "anthropic": {"model_type": ChatModel.ModelType.ANTHROPIC, "name": "Anthropic"},
        "google": {"model_type": ChatModel.ModelType.GOOGLE, "name": "Google Gemini"},
    }

    model_tiers = config.get("model_tiers", {})

    # --- 1. Providers and chat models ---
    for provider_key, provider_config in config.get("providers", {}).items():
        meta = provider_meta.get(provider_key)
        if not meta:
            logger.warning(f"Bootstrap: unknown provider '{provider_key}', skipping.")
            continue

        api_key = provider_config.get("api_key")
        if not api_key:
            logger.warning(f"Bootstrap: provider '{provider_key}' has no api_key, skipping.")
            continue

        # AiModelApi.name is not unique — use filter().first() to avoid MultipleObjectsReturned.
        ai_model_api = AiModelApi.objects.filter(name=meta["name"]).first()
        if ai_model_api:
            ai_model_api.api_key = api_key
            ai_model_api.api_base_url = provider_config.get("base_url")
            ai_model_api.save()
            logger.info(f"Bootstrap: {meta['name']} provider updated")
        else:
            ai_model_api = AiModelApi.objects.create(
                name=meta["name"], api_key=api_key, api_base_url=provider_config.get("base_url")
            )
            logger.info(f"Bootstrap: {meta['name']} provider created")

        vision_models = set(provider_config.get("vision_models", []))
        for model_name in provider_config.get("chat_models", []):
            tier_str = model_tiers.get(model_name, "free").lower()
            price_tier = PriceTier.STANDARD if tier_str == "standard" else PriceTier.FREE

            model_defaults = {
                "friendly_name": model_name,
                "model_type": meta["model_type"],
                "vision_enabled": model_name in vision_models,
                "max_prompt_size": model_to_prompt_size.get(model_name),
                "tokenizer": model_to_tokenizer.get(model_name),
                "ai_model_api": ai_model_api,
                "price_tier": price_tier,
            }
            # ChatModel.name is not unique — use filter().first() to avoid MultipleObjectsReturned.
            existing = ChatModel.objects.filter(name=model_name).first()
            if existing:
                for key, value in model_defaults.items():
                    setattr(existing, key, value)
                existing.save()
            else:
                ChatModel.objects.create(name=model_name, **model_defaults)

    # --- 2. Embedding configuration ---
    embedding = config.get("embedding")
    if embedding and embedding.get("model"):
        api_type_str = embedding.get("api_type", "local").upper()
        valid_types = {t.value.upper(): t.value for t in SearchModelConfig.ApiType}  # type: ignore[attr-defined]
        if api_type_str not in valid_types:
            logger.warning(f"Bootstrap: invalid embedding api_type '{embedding.get('api_type')}', skipping.")
        else:
            defaults = {
                "bi_encoder": embedding["model"],
                "embeddings_inference_endpoint_type": valid_types[api_type_str],
            }
            if embedding.get("dimensions") is not None:
                try:
                    defaults["bi_encoder_dimensions"] = int(embedding["dimensions"])
                except (ValueError, TypeError):
                    logger.warning(f"Bootstrap: invalid embedding dimensions '{embedding['dimensions']}', skipping.")
            if embedding.get("api_key"):
                defaults["embeddings_inference_endpoint_api_key"] = embedding["api_key"]
            if embedding.get("endpoint"):
                defaults["embeddings_inference_endpoint"] = embedding["endpoint"]
            if embedding.get("cross_encoder"):
                defaults["cross_encoder"] = embedding["cross_encoder"]

            _, created = SearchModelConfig.objects.update_or_create(name="default", defaults=defaults)
            logger.info(
                f"Bootstrap: embedding config {'created' if created else 'updated'} (model: {embedding['model']})"
            )

    # --- 3. Server chat slot defaults ---
    slot_defaults = config.get("defaults")
    if slot_defaults:
        from django.core.exceptions import ValidationError

        valid_slots = {slot.value for slot in ServerChatSettings.ChatModelSlot}  # type: ignore[attr-defined]
        free_tier_slots = {"chat_default", "think_free_fast", "think_free_deep"}

        server_settings = ServerChatSettings.objects.first()
        if not server_settings:
            server_settings = ServerChatSettings()

        any_set = False
        for slot_name, model_name in slot_defaults.items():
            if not model_name or slot_name not in valid_slots:
                if slot_name not in valid_slots:
                    logger.warning(f"Bootstrap: unknown slot '{slot_name}', skipping.")
                continue

            chat_model = ChatModel.objects.filter(name=model_name).first()
            if not chat_model:
                logger.error(f"Bootstrap: model '{model_name}' not found for slot '{slot_name}', skipping.")
                continue

            if slot_name in free_tier_slots and chat_model.price_tier != PriceTier.FREE:
                logger.warning(
                    f"Bootstrap: model '{model_name}' has tier '{chat_model.price_tier}' but slot "
                    f"'{slot_name}' requires FREE. Skipping."
                )
                continue

            setattr(server_settings, slot_name, chat_model)
            any_set = True
            logger.info(f"Bootstrap: slot '{slot_name}' set to '{model_name}'")

        if any_set:
            try:
                server_settings.save()
            except ValidationError as e:
                logger.error(f"Bootstrap: failed to save server chat settings: {e}")

    # --- 4. Team models ---
    team_models = config.get("team_models")
    if team_models:
        from apollos.database.models import Team

        for team_slug, team_config in team_models.items():
            team = Team.objects.filter(slug=team_slug).first()
            if not team:
                logger.warning(f"Bootstrap: team '{team_slug}' not found, skipping model assignment.")
                continue

            # Resolve model names to PKs
            model_ids = []
            for model_name in team_config.get("allowed_models", []):
                cm = ChatModel.objects.filter(name=model_name).first()
                if cm:
                    model_ids.append(cm.id)
                else:
                    logger.warning(f"Bootstrap: model '{model_name}' not found for team '{team_slug}', skipping.")

            team.settings["allowed_models"] = model_ids

            # Optional team default override
            default_name = team_config.get("chat_default")
            if default_name:
                cm = ChatModel.objects.filter(name=default_name).first()
                if cm:
                    team.settings["chat_default"] = cm.id
                else:
                    logger.warning(f"Bootstrap: default model '{default_name}' not found for team '{team_slug}'.")

            team.save()
            logger.info(f"Bootstrap: team '{team_slug}' assigned {len(model_ids)} model(s)")
