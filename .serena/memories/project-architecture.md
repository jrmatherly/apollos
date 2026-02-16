# Apollos - Project Architecture

## Overview
Apollos AI is a production-ready personal assistant / semantic search application ("Your Second Brain").
Forked/migrated from the Khoj project. Python 3.10-3.12, Django 5.1 + FastAPI hybrid.

## Tech Stack
- **Web Framework**: Django 5.1 (ORM, admin, auth) + FastAPI (API endpoints)
- **Database**: PostgreSQL with pgvector for vector similarity search
- **ML/AI**: PyTorch 2.6, sentence-transformers 3.4, LangChain text splitters
- **LLM Providers**: OpenAI, Anthropic, Google (Gemini)
- **Document Processing**: PyMuPDF, RapidOCR, python-docx, BeautifulSoup
- **Voice**: OpenAI Whisper
- **Build**: Hatchling with hatch-vcs

## Directory Structure
```
src/
├── apollos/              # Core application
│   ├── main.py           # Application entry point
│   ├── configure.py      # Configuration + require_admin() RBAC
│   ├── manage.py         # Django management
│   ├── routers/          # FastAPI API endpoints
│   │   ├── api.py        # Main API router
│   │   ├── api_chat.py   # Chat endpoints
│   │   ├── api_content.py # Content management
│   │   ├── api_model.py  # Model config + admin + team model endpoints
│   │   ├── api_agents.py # Agent endpoints
│   │   ├── api_memories.py # Memory endpoints
│   │   ├── auth.py       # Authentication
│   │   ├── research.py   # Research mode
│   │   └── ...
│   ├── database/         # Django models & migrations
│   │   ├── models/       # Data models (incl. Organization, Team, TeamMembership)
│   │   ├── adapters/     # Database adapters (incl. get_available_chat_models)
│   │   ├── management/commands/  # bootstrap_models command
│   │   └── migrations/   # Django migrations (latest: 0101)
│   ├── processor/        # Data processing pipeline
│   │   ├── content/      # Document processors
│   │   ├── conversation/ # Chat/conversation handling
│   │   ├── tools/        # Tool implementations
│   │   ├── operator/     # Operator logic
│   │   ├── speech/       # Voice processing
│   │   ├── image/        # Image processing
│   │   └── embeddings.py # Embedding generation (supports configurable dimensions)
│   ├── search_type/      # Search implementations
│   ├── search_filter/    # Search filtering
│   ├── utils/            # Shared utilities
│   ├── interface/        # Web UI assets
│   └── app/              # Django app config
├── interface/            # Client interfaces
│   ├── web/              # Web frontend (primary)
│   └── obsidian/         # Obsidian plugin (planned)
└── telemetry/            # Telemetry service

tests/                    # Test suite (pytest)
documentation/            # Project docs
```

NOTE: `src/interface/android/`, `src/interface/emacs/`, and `src/interface/desktop/` have been removed. Focus is on web and eventually Obsidian.

## Model Configuration System (Phases 1-6 Complete)
6-phase environment variable and bootstrap configuration:
1. **Embedding env vars** (`APOLLOS_EMBEDDING_MODEL`, `_DIMENSIONS`, `_API_TYPE`, `_API_KEY`, `_ENDPOINT`, `APOLLOS_CROSS_ENCODER_MODEL`) — apply only when creating NEW SearchModelConfig records
2. **Chat model list env vars** (`APOLLOS_OPENAI_CHAT_MODELS`, `_GEMINI_`, `_ANTHROPIC_`) — evaluated at module import time in `utils/constants.py`
3. **Server chat slot env vars** (`APOLLOS_DEFAULT_CHAT_MODEL`, `_ADVANCED_`, `_THINK_FREE_FAST_`, `_THINK_FREE_DEEP_`, `_THINK_PAID_FAST_`, `_THINK_PAID_DEEP_`) — always override bootstrap slots
4. **Bootstrap config file** (`APOLLOS_BOOTSTRAP_CONFIG`) — JSONC with `${VAR}` interpolation, idempotent create/update. Example: `bootstrap.example.jsonc`
5. **Team model assignment** — `Team.settings["allowed_models"]` (ChatModel PKs), `get_available_chat_models(user)` returns global + team models, admin CRUD endpoints
6. **Admin API** — `GET/POST /api/model/chat/defaults`, `GET /api/model/embedding`, protected by `require_admin()`

Key files: `utils/bootstrap.py`, `utils/constants.py`, `utils/initialization.py`, `database/management/commands/bootstrap_models.py`
Plans: `.scratchpad/litellm-models/plan.md`, `.scratchpad/plans/2026-02-15-enterprise-foundation-unblock-phases-5-6.md`

## Enterprise Foundation (Complete)
Models added to support team-based features and admin RBAC:
- **Organization** — Single org (name, slug, settings JSONField)
- **Team** — Teams within org (name, slug, settings JSONField for allowed_models/chat_default)
- **TeamMembership** — User-team mapping with roles (admin, team_lead, member)
- **ApollosUser.is_org_admin** — Boolean for org admin access
- **require_admin(request)** — In `configure.py`, checks `is_org_admin` or `is_staff`
- **Migration**: `0101_organization_team_teammembership`
- Auth pattern: `@requires(["authenticated"])` + `require_admin(request)` — NOT `Depends()`

Future scope (not yet implemented): Entra ID SSO, Entry/Agent model changes, MCP registry, full RBAC factory, Organization.settings convergence

## Development Environment (mise-en-place)

The project uses [mise](https://mise.jdx.dev) for tool version management and task automation.
Config: `mise.toml` at project root.

**Managed tools:** Python 3.12, Bun 1.x, uv (latest)
**Auto-configured:** `.venv` activation on `cd`, `DJANGO_SETTINGS_MODULE`, DB defaults
**Task runner:** 40 tasks — `mise run dev`, `mise run test`, `mise run docker:up`, etc.

Key tasks:
- `mise run setup` — first-time project setup (deps + migrate + frontend)
- `mise run deps` — install Python deps (handles openai-whisper/setuptools workaround)
- `mise run dev` — start server at port 42110
- `mise run ci` — full CI pipeline (lint + format:check + test:unit)
- `mise run docker:db` — start only PostgreSQL
- `mise run db:migrate` / `mise run db:makemigrations` — Django migrations
- `mise run manage <cmd>` — any Django management command

Local overrides: `mise.local.toml` (gitignored) for API keys, custom DB config, etc.

## Key Patterns
- Hybrid Django/FastAPI: Django for ORM and admin, FastAPI for API routes
- Vector search via pgvector extension in PostgreSQL
- Multi-provider LLM support with fallback/retry (tenacity)
- Document ingestion pipeline: parse → chunk → embed → store
- Authentication via authlib + Django auth
- Admin auth: `@requires(["authenticated"])` + `require_admin(request)` (not Depends)
- AiModelApi.name and ChatModel.name are NOT unique — use filter().first() pattern, not update_or_create
- Team model filtering: user's available models = global defaults + union of team-assigned models
- Anonymous mode: `GET /chat/options` returns all models for unauthenticated users (no @requires on endpoint)
