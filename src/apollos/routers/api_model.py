import json
import logging
from typing import Dict, Optional, Union

from fastapi import APIRouter, Request
from fastapi.responses import Response
from starlette.authentication import has_required_scope, requires

from apollos.database.adapters import ConversationAdapters
from apollos.database.models import (
    ChatModel,
    PriceTier,
    SearchModelConfig,
    ServerChatSettings,
    TextToImageModelConfig,
    VoiceModelOption,
)
from apollos.routers.helpers import update_telemetry_state

api_model = APIRouter()
logger = logging.getLogger(__name__)


@api_model.get("/chat/options", response_model=Dict[str, Union[str, int]])
def get_chat_model_options(
    request: Request,
    client: Optional[str] = None,
):
    if request.user.is_authenticated and hasattr(request.user, "object"):
        user = request.user.object
        chat_models = ConversationAdapters.get_available_chat_models(user)
    else:
        # Anonymous/unauthenticated: return all models (current behavior)
        chat_models = ConversationAdapters.get_conversation_processor_options().all()

    chat_model_options = list()
    for chat_model in chat_models:
        chat_model_options.append(
            {
                "name": chat_model.friendly_name,
                "id": chat_model.id,
                "strengths": chat_model.strengths,
                "description": chat_model.description,
            }
        )

    return Response(content=json.dumps(chat_model_options), media_type="application/json", status_code=200)


@api_model.get("/chat")
@requires(["authenticated"])
def get_user_chat_model(
    request: Request,
    client: Optional[str] = None,
):
    user = request.user.object

    chat_model = ConversationAdapters.get_chat_model(user)

    if chat_model is None:
        chat_model = ConversationAdapters.get_default_chat_model(user)

    return Response(status_code=200, content=json.dumps({"id": chat_model.id, "chat_model": chat_model.friendly_name}))


@api_model.post("/chat", status_code=200)
@requires(["authenticated"])
async def update_chat_model(
    request: Request,
    id: str,
    client: Optional[str] = None,
):
    user = request.user.object
    subscribed = has_required_scope(request, ["premium"])

    # Validate if model can be switched
    chat_model = await ChatModel.objects.filter(id=int(id)).afirst()
    if chat_model is None:
        return Response(status_code=404, content=json.dumps({"status": "error", "message": "Chat model not found"}))
    if not subscribed and chat_model.price_tier != PriceTier.FREE:
        return Response(
            status_code=403,
            content=json.dumps({"status": "error", "message": "Subscribe to switch to this chat model"}),
        )

    # Validate model is in user's available set
    available = await ConversationAdapters.aget_available_chat_models(user)
    if not await available.filter(id=chat_model.id).aexists():
        return Response(
            status_code=403,
            content=json.dumps({"status": "error", "message": "This model is not available for your account"}),
            media_type="application/json",
        )

    new_config = await ConversationAdapters.aset_user_conversation_processor(user, int(id))

    update_telemetry_state(
        request=request,
        telemetry_type="api",
        api="set_conversation_chat_model",
        client=client,
        metadata={"processor_conversation_type": "conversation"},
    )

    if new_config is None:
        return {"status": "error", "message": "Model not found"}

    return {"status": "ok"}


@api_model.post("/voice", status_code=200)
@requires(["authenticated"])
async def update_voice_model(
    request: Request,
    id: str,
    client: Optional[str] = None,
):
    user = request.user.object
    subscribed = has_required_scope(request, ["premium"])

    # Validate if model can be switched
    voice_model = await VoiceModelOption.objects.filter(model_id=id).afirst()
    if voice_model is None:
        return Response(status_code=404, content=json.dumps({"status": "error", "message": "Voice model not found"}))
    if not subscribed and voice_model.price_tier != PriceTier.FREE:
        return Response(
            status_code=403,
            content=json.dumps({"status": "error", "message": "Subscribe to switch to this voice model"}),
        )

    new_config = await ConversationAdapters.aset_user_voice_model(user, id)

    update_telemetry_state(
        request=request,
        telemetry_type="api",
        api="set_voice_model",
        client=client,
    )

    if new_config is None:
        return Response(status_code=404, content=json.dumps({"status": "error", "message": "Model not found"}))

    return Response(status_code=202, content=json.dumps({"status": "ok"}))


@api_model.post("/paint", status_code=200)
@requires(["authenticated"])
async def update_paint_model(
    request: Request,
    id: str,
    client: Optional[str] = None,
):
    user = request.user.object
    subscribed = has_required_scope(request, ["premium"])

    # Validate if model can be switched
    image_model = await TextToImageModelConfig.objects.filter(id=int(id)).afirst()
    if image_model is None:
        return Response(status_code=404, content=json.dumps({"status": "error", "message": "Image model not found"}))
    if not subscribed and image_model.price_tier != PriceTier.FREE:
        return Response(
            status_code=403,
            content=json.dumps({"status": "error", "message": "Subscribe to switch to this image model"}),
        )

    new_config = await ConversationAdapters.aset_user_text_to_image_model(user, int(id))

    update_telemetry_state(
        request=request,
        telemetry_type="api",
        api="set_paint_model",
        client=client,
        metadata={"paint_model": new_config.setting.model_name},
    )

    if new_config is None:
        return {"status": "error", "message": "Model not found"}

    return {"status": "ok"}


@api_model.get("/team/{team_slug}/models")
@requires(["authenticated"])
def get_team_models(request: Request, team_slug: str):
    """Get models assigned to a team. Admin-only."""
    from apollos.configure import require_admin
    from apollos.database.models import Team

    require_admin(request)
    team = Team.objects.filter(slug=team_slug).first()
    if not team:
        return Response(status_code=404, content=json.dumps({"error": "Team not found"}), media_type="application/json")

    model_ids = team.settings.get("allowed_models", [])
    models = ChatModel.objects.filter(id__in=model_ids)
    result = [{"id": m.id, "name": m.name, "friendly_name": m.friendly_name} for m in models]
    return Response(content=json.dumps(result), media_type="application/json")


@api_model.post("/team/{team_slug}/models")
@requires(["authenticated"])
def set_team_models(request: Request, team_slug: str, body: dict):
    """Assign models to a team. Admin-only."""
    from apollos.configure import require_admin
    from apollos.database.models import Team

    require_admin(request)
    team = Team.objects.filter(slug=team_slug).first()
    if not team:
        return Response(status_code=404, content=json.dumps({"error": "Team not found"}), media_type="application/json")

    model_ids = body.get("model_ids", [])
    # Validate all model IDs exist
    valid_models = ChatModel.objects.filter(id__in=model_ids)
    team.settings["allowed_models"] = [m.id for m in valid_models]

    if "chat_default" in body and body["chat_default"]:
        default_model = ChatModel.objects.filter(id=body["chat_default"]).first()
        if not default_model:
            return Response(
                status_code=400,
                content=json.dumps({"error": f"chat_default model ID {body['chat_default']} not found"}),
                media_type="application/json",
            )
        if default_model.id not in team.settings["allowed_models"]:
            return Response(
                status_code=400,
                content=json.dumps({"error": "chat_default must be in the team's allowed_models list"}),
                media_type="application/json",
            )
        team.settings["chat_default"] = default_model.id

    team.save()
    return Response(
        content=json.dumps({"status": "ok", "assigned_models": len(valid_models)}),
        media_type="application/json",
    )


@api_model.delete("/team/{team_slug}/models/{model_id}")
@requires(["authenticated"])
def remove_team_model(request: Request, team_slug: str, model_id: int):
    """Remove a model from team access. Admin-only."""
    from apollos.configure import require_admin
    from apollos.database.models import Team

    require_admin(request)
    team = Team.objects.filter(slug=team_slug).first()
    if not team:
        return Response(status_code=404, content=json.dumps({"error": "Team not found"}), media_type="application/json")

    model_ids = team.settings.get("allowed_models", [])
    if model_id in model_ids:
        model_ids.remove(model_id)
        team.settings["allowed_models"] = model_ids
        team.save()

    return Response(content=json.dumps({"status": "ok"}), media_type="application/json")


@api_model.get("/chat/defaults")
@requires(["authenticated"])
def get_chat_defaults(request: Request):
    """Get current ServerChatSettings slot assignments. Admin-only."""
    from apollos.configure import require_admin

    require_admin(request)
    server_settings = ServerChatSettings.objects.first()
    if not server_settings:
        return Response(content=json.dumps({}), media_type="application/json")

    def slot_info(model):
        if not model:
            return None
        return {"id": model.id, "name": model.name, "price_tier": str(model.price_tier)}

    result = {
        "chat_default": slot_info(server_settings.chat_default),
        "chat_advanced": slot_info(server_settings.chat_advanced),
        "think_free_fast": slot_info(server_settings.think_free_fast),
        "think_free_deep": slot_info(server_settings.think_free_deep),
        "think_paid_fast": slot_info(server_settings.think_paid_fast),
        "think_paid_deep": slot_info(server_settings.think_paid_deep),
    }
    return Response(content=json.dumps(result), media_type="application/json")


@api_model.post("/chat/defaults")
@requires(["authenticated"])
def update_chat_defaults(request: Request, body: dict):
    """Update ServerChatSettings slots. Admin-only. Body: {slot_name: model_id}.

    Atomic: if any slot assignment fails validation, no changes are saved.
    """
    from apollos.configure import require_admin

    require_admin(request)

    valid_slots = {
        "chat_default",
        "chat_advanced",
        "think_free_fast",
        "think_free_deep",
        "think_paid_fast",
        "think_paid_deep",
    }
    free_tier_slots = {"chat_default", "think_free_fast", "think_free_deep"}

    server_settings = ServerChatSettings.objects.first()
    if not server_settings:
        server_settings = ServerChatSettings()

    errors = []
    for slot_name, model_id in body.items():
        if slot_name not in valid_slots:
            continue
        if model_id is None:
            setattr(server_settings, slot_name, None)
            continue

        chat_model = ChatModel.objects.filter(id=model_id).first()
        if not chat_model:
            errors.append(f"Model ID {model_id} not found for slot '{slot_name}'")
            continue
        if slot_name in free_tier_slots and chat_model.price_tier != PriceTier.FREE:
            errors.append(f"Slot '{slot_name}' requires FREE tier model, got '{chat_model.price_tier}'")
            continue
        setattr(server_settings, slot_name, chat_model)

    if errors:
        return Response(
            status_code=400,
            content=json.dumps({"status": "error", "errors": errors}),
            media_type="application/json",
        )

    try:
        server_settings.save()
    except Exception as e:
        return Response(
            status_code=500,
            content=json.dumps({"status": "error", "message": str(e)}),
            media_type="application/json",
        )

    return Response(content=json.dumps({"status": "ok"}), media_type="application/json")


@api_model.get("/embedding")
@requires(["authenticated"])
def get_embedding_config(request: Request):
    """Get current embedding model configuration. Admin-only."""
    from apollos.configure import require_admin

    require_admin(request)
    search_config = SearchModelConfig.objects.filter(name="default").first()
    if not search_config:
        return Response(content=json.dumps({}), media_type="application/json")

    result = {
        "bi_encoder": search_config.bi_encoder,
        "bi_encoder_dimensions": search_config.bi_encoder_dimensions,
        "api_type": search_config.embeddings_inference_endpoint_type,
        "cross_encoder": search_config.cross_encoder,
        "has_api_key": bool(search_config.embeddings_inference_endpoint_api_key),
        "has_endpoint": bool(search_config.embeddings_inference_endpoint),
    }
    return Response(content=json.dumps(result), media_type="application/json")


@api_model.post("/embedding")
@requires(["authenticated"])
def update_embedding_config(request: Request, body: dict):
    """Update embedding model configuration. Admin-only.

    Warns about re-indexing requirement if bi_encoder model changes.

    Accepts embeddings_inference_endpoint_api_key for configuration (admin-only).
    GET /embedding intentionally returns only has_api_key:bool, never the raw key.
    """
    from apollos.configure import require_admin
    from apollos.database.models import Entry

    require_admin(request)

    search_config = SearchModelConfig.objects.filter(name="default").first()
    if not search_config:
        search_config = SearchModelConfig(name="default")

    requires_reindex = False
    old_model = search_config.bi_encoder

    updatable_fields = {
        "bi_encoder": str,
        "bi_encoder_dimensions": lambda v: int(v) if v is not None else None,
        "cross_encoder": str,
        "embeddings_inference_endpoint_type": str,
        "embeddings_inference_endpoint": lambda v: v,
        "embeddings_inference_endpoint_api_key": lambda v: v,
    }

    for field, converter in updatable_fields.items():
        if field in body:
            try:
                setattr(search_config, field, converter(body[field]))
            except (ValueError, TypeError) as e:
                return Response(
                    status_code=400,
                    content=json.dumps({"status": "error", "message": f"Invalid value for '{field}': {e}"}),
                    media_type="application/json",
                )

    # Detect if model changed (requires re-indexing)
    if search_config.bi_encoder != old_model:
        requires_reindex = True

    try:
        search_config.save()
    except Exception as e:
        return Response(
            status_code=500,
            content=json.dumps({"status": "error", "message": str(e)}),
            media_type="application/json",
        )

    result = {"status": "ok", "requires_reindex": requires_reindex}
    if requires_reindex:
        result["affected_entries"] = Entry.objects.count()
        result["warning"] = "Embedding model changed. All entries must be re-indexed for search to work correctly."

    return Response(content=json.dumps(result), media_type="application/json")
