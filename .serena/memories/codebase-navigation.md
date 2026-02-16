# Apollos Codebase Navigation Guide

## Quick Reference - Where to Find Things

### API Endpoints
- All routers: `src/apollos/routers/`
- Chat API: `src/apollos/routers/api_chat.py` (25+ endpoints including WebSocket)
- Content API: `src/apollos/routers/api_content.py` (indexing, CRUD)
- Model API: `src/apollos/routers/api_model.py` (model selection, admin defaults, team models, embedding config)
- Router helpers & rate limiters: `src/apollos/routers/helpers.py` (large file, many utilities)

### Admin API Endpoints (in api_model.py)
- `GET/POST /api/model/chat/defaults` — ServerChatSettings slot management (admin-only)
- `GET /api/model/embedding` — Embedding model config view (admin-only)
- `GET/POST/DELETE /api/model/team/{team_slug}/models` — Team model assignment (admin-only)
- `GET /api/model/chat/options` — Team-filtered model list (auth-aware, anonymous gets all models)
- `POST /api/model/chat` — Model selection with team-aware validation

### Data Models
- All models in single file: `src/apollos/database/models/__init__.py`
- Core models: ApollosUser, Conversation, Agent, Entry, ChatModel, FileObject, UserMemory
- Enterprise models: Organization, Team, TeamMembership
- ApollosUser.is_org_admin — org-level admin flag
- Adapters (data access): `src/apollos/database/adapters/__init__.py` (very large, all adapter classes)
- Key adapter: `ConversationAdapters.get_available_chat_models(user)` — team-filtered model list

### Auth & RBAC
- Auth backend: `src/apollos/configure.py` (UserAuthenticationBackend)
- Admin check: `require_admin(request)` in `src/apollos/configure.py` — checks is_org_admin or is_staff
- Pattern: `@requires(["authenticated"])` decorator + `require_admin(request)` inline call
- NOT using FastAPI `Depends()` — codebase uses starlette auth pattern

### LLM Integration
- OpenAI: `src/apollos/processor/conversation/openai/gpt.py`
- Anthropic: `src/apollos/processor/conversation/anthropic/anthropic_chat.py`
- Google: `src/apollos/processor/conversation/google/gemini_chat.py`
- All prompts: `src/apollos/processor/conversation/prompts.py` (~40+ prompt templates)
- Chat utilities: `src/apollos/processor/conversation/utils.py`

### Search System
- Text search core: `src/apollos/search_type/text_search.py`
- Embedding models: `src/apollos/processor/embeddings.py` (supports configurable dimensions)
- Search filters: `src/apollos/search_filter/` (date, file, word, base)

### Document Processing
- PDF: `src/apollos/processor/content/pdf/pdf_to_entries.py`
- Markdown: `src/apollos/processor/content/markdown/markdown_to_entries.py`
- Org-mode: `src/apollos/processor/content/org_mode/org_to_entries.py`
- Others: docx, plaintext, images, github, notion under `processor/content/`

### Tools
- Web search: `src/apollos/processor/tools/online_search.py` (Google, Serper, SearXNG, Exa, Firecrawl)
- Code execution: `src/apollos/processor/tools/run_code.py`
- MCP integration: `src/apollos/processor/tools/mcp.py`

### Computer Use / Operator
- Base classes: `src/apollos/processor/operator/operator_agent_base.py`
- Provider implementations: operator_agent_openai.py, operator_agent_anthropic.py
- Environments: operator_environment_browser.py, operator_environment_computer.py

### Client Interfaces
- Web frontend (primary): `src/interface/web/` — Next.js + shadcn/ui
- Obsidian plugin (planned): `src/interface/obsidian/`
- NOTE: android, emacs, desktop interfaces have been removed

### Frontend (Web)
- Next.js app: `src/interface/web/`
- Pages: chat, settings, agents, search, automations, share
- Components: `src/interface/web/app/components/` (20+ component directories)
- UI primitives: `src/interface/web/components/ui/` (shadcn)
- Model selector: `src/interface/web/app/common/modelSelector.tsx` (renders server-filtered list)

### Configuration & Utilities
- Server bootstrap: `src/apollos/configure.py` (also contains require_admin)
- Core helpers: `src/apollos/utils/helpers.py` (ConversationCommand enum, LLM clients)
- Pydantic configs: `src/apollos/utils/rawconfig.py`
- Django settings: `src/apollos/app/settings.py`
- Model constants: `src/apollos/utils/constants.py` (env-var-driven model lists, evaluated at import time)
- Bootstrap config: `src/apollos/utils/bootstrap.py` (JSONC loader, idempotent model/provider/slot/team setup)
- Bootstrap example: `bootstrap.example.jsonc` (JSONC format — supports comments and trailing commas)
- Server initialization: `src/apollos/utils/initialization.py` (admin user, bootstrap, chat setup, slot config)
- Bootstrap management command: `python manage.py bootstrap_models --config path/to/bootstrap.jsonc`

### Migrations
- Latest: `0101_organization_team_teammembership` (enterprise foundation)
- Previous: `0100_add_bi_encoder_dimensions_to_searchmodelconfig` (embedding dimensions)

### Testing
- All tests: `tests/` directory
- Test config: `pytest.ini`
- Test factories: `tests/helpers.py` (UserFactory, ChatModelFactory, AiModelApiFactory, OrganizationFactory, TeamFactory, TeamMembershipFactory)
- Model config tests: `tests/test_model_configuration.py`
- Key test areas: conversation, search, document processing, API, agents, model configuration
- NOTE: Some test data files (`tests/data/org/`, `tests/helpers.py` content strings) still reference emacs — these are document content fixtures for testing the text parsing pipeline, not instructions to use emacs
