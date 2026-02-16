# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Summary

Apollos AI (forked from Khoj) is a personal assistant with semantic search capabilities. Domain: `*.apollosai.dev`. It uses a **hybrid Django + FastAPI** architecture: Django handles ORM, admin, auth, and migrations; FastAPI handles all API endpoints. Data is stored in PostgreSQL with pgvector for vector similarity search. The app supports multiple LLM providers (OpenAI, Anthropic, Google Gemini).

## Development Setup

### Using mise (Recommended)

The project uses [mise-en-place](https://mise.jdx.dev) for tool version management, virtual environment activation, and task automation. Install mise first: `curl https://mise.run | sh`

```bash
git clone https://github.com/jrmatherly/apollos && cd apollos
mise install          # Installs Python 3.12, bun, uv (pinned versions)
mise run setup        # Installs all deps, runs migrations, builds frontend
mise run dev          # Starts server at port 42110
```

mise automatically activates the `.venv` virtual environment when you `cd` into the project — no manual `source .venv/bin/activate` needed. It also sets `DJANGO_SETTINGS_MODULE` and database defaults.

Run `mise tasks ls` to see all available tasks, or `mise run` for an interactive picker.

### Manual Setup (Without mise)

```bash
# Install Python dependencies (requires Python 3.10-3.12)
uv venv && uv pip install setuptools && uv sync --all-extras --no-build-isolation-package openai-whisper

# Install web frontend (Next.js + Tailwind + shadcn/ui)
cd src/interface/web && bun install && bun run export

# Install pre-commit hooks
pre-commit install -t pre-push -t pre-commit

# Full setup (includes Obsidian plugin)
./scripts/dev_setup.sh --full
```

**Database**: Requires PostgreSQL with pgvector extension. Default connection: `localhost:5432`, user `postgres`, db `apollos`. Or use `docker compose up database` (or `mise run docker:db`) to start one. Set `USE_EMBEDDED_DB=True` for pgserver (embedded PostgreSQL for local dev).

## Common Commands

All commands are available as mise tasks (`mise run <task>`). Raw commands shown for reference.

```bash
# Run the server (default port 42110)
mise run dev                          # or: apollos --host 0.0.0.0 --port 42110 -vv

# Run all tests (requires PostgreSQL)
mise run test                         # or: pytest
mise run test:unit                    # skip chat quality tests

# Run a single test file
pytest tests/test_helpers.py
pytest tests/test_helpers.py::test_function_name -v

# Lint and format
mise run lint:fix                     # or: ruff check --fix src/apollos/
mise run format                       # or: ruff format src/apollos/

# Type check
mise run typecheck                    # or: mypy --config-file=pyproject.toml

# Django management (migrations etc.)
mise run db:migrate                   # or: python src/apollos/manage.py migrate
mise run db:makemigrations            # or: python src/apollos/manage.py makemigrations database
mise run manage <command>             # any manage.py command

# Docker
mise run docker:up                    # start all services
mise run docker:db                    # start only database
mise run docker:logs                  # follow logs

# Full CI pipeline
mise run ci                           # lint + format check + unit tests

# Apply bootstrap model configuration
mise run manage bootstrap_models -- --config /path/to/bootstrap.jsonc
```

### mise Task Reference

| Task | Description |
|------|-------------|
| `setup` | First-time setup: deps + migrate + frontend |
| `deps` | Install Python deps (handles openai-whisper workaround) |
| `dev` | Start backend server (port 42110) |
| `dev:web` | Start frontend dev server (hot reload) |
| `docker:up/down/logs/ps/db` | Docker Compose lifecycle |
| `db:migrate/makemigrations/reset` | Django migration workflow |
| `lint/lint:fix/format/typecheck` | Code quality tools |
| `test/test:unit/test:chat/test:coverage` | Test runners |
| `manage/shell/admin:create` | Django management |
| `ci` | Full CI pipeline |
| `env` | Show environment info |
| `clean` | Remove build artifacts |

## Architecture

### Hybrid Django + FastAPI

The app starts in `src/apollos/main.py`:
1. Django is initialized first (`django.setup()`, migrations, static files)
2. A FastAPI app is created and routes are configured via `configure.py`
3. Django ASGI app is mounted at `/server` (admin panel, auth pages)
4. Starlette middleware handles authentication, sessions, CORS, connection cleanup

**Key implication**: Django must be fully initialized before any FastAPI imports that reference models. The import order in `main.py` matters (see `isort:skip_file`).

### Request Authentication Flow

Authentication happens in `configure.py:UserAuthenticationBackend`:
1. Session-based auth (web): checks `request.session["user"]["email"]`
2. Bearer token auth (API clients): looks up `ApollosApiUser.token`
3. Client ID + secret auth (WhatsApp): validates `ClientApplication`
4. Anonymous mode: creates/uses a default user when `state.anonymous_mode` is True

### Data Flow: Chat Request

```text
api_chat.py (chat/chat_ws) → routers/helpers.py (process, search, tool dispatch)
  → processor/conversation/{openai,anthropic,google}/ (LLM call)
  → processor/tools/ (online_search, run_code, mcp) if tools needed
  → database/adapters (save conversation log)
  → SSE stream or WebSocket response
```

### Data Flow: Content Indexing

```text
api_content.py (put_content) → processor/content/*_to_entries.py (parse)
  → text_to_entries.py (chunk) → embeddings.py (embed)
  → Entry model (store in PostgreSQL with pgvector)
```

### Search Pipeline

`search_type/text_search.py`: query embedding → pgvector similarity search → filter (date/file/word) → cross-encoder reranking → deduplicate

### Key Modules

- **`database/models/__init__.py`**: All Django models in a single file. Core entities: `ApollosUser`, `Conversation`, `Agent`, `Entry`, `ChatModel`, `FileObject`, `UserMemory`. Enterprise models: `Organization`, `Team`, `TeamMembership`.
- **`database/adapters/__init__.py`**: All database access logic. Adapter classes (`ConversationAdapters`, `AgentAdapters`, `EntryAdapters`, etc.) provide the data access API. Many methods have both sync and async variants (prefixed with `a`). `ConversationAdapters.get_available_chat_models(user)` returns team-filtered models.
- **`processor/conversation/prompts.py`**: All LLM prompt templates (~40+ variables). Modify here when changing AI behavior.
- **`routers/helpers.py`**: Core chat processing logic, rate limiters, tool dispatch, content search. This is the largest and most complex router helper.
- **`utils/helpers.py`**: `ConversationCommand` enum (controls chat behavior), LLM client factory functions, device detection, token counting.
- **`utils/constants.py`**: Default chat model lists per provider (read from env vars at import time), model-to-cost pricing dict, app paths.
- **`utils/bootstrap.py`**: JSONC bootstrap config loader and applicator. Idempotently creates providers, chat models, embedding config, server chat slots, and team model assignments from a single config file.
- **`utils/initialization.py`**: Server bootstrap sequence — admin user, bootstrap config, chat model setup, Ollama discovery, server chat slot configuration.
- **`pyproject.toml`**: The `dev` extras use `"apollos[prod,local]"` — this is a self-referencing dependency resolved locally, not fetched from PyPI.

### Documentation

Project documentation lives at `documentation/` (Docusaurus site). Feature docs, client guides, and architecture references are at `documentation/docs/`. When completing a feature implementation, convert the implementation plan into proper documentation here.

### Frontend (Web)

Next.js app at `src/interface/web/`. Pages: chat, settings, agents, search, automations, share. Components in `app/components/`. UI primitives use shadcn/ui. Frontend domain config is centralized in `src/interface/web/app/common/config.ts` — import `APP_URL`, `DOCS_URL`, `ASSETS_URL`, `SUPPORT_EMAIL` from there, never hardcode.

## Testing

- Tests require a running PostgreSQL database with pgvector
- `pytest.ini` sets `DJANGO_SETTINGS_MODULE=apollos.app.settings` and `--reuse-db`
- Chat-related tests need an LLM API key (`OPENAI_API_KEY`, `GEMINI_API_KEY`, or `ANTHROPIC_API_KEY`). Set `APOLLOS_TEST_CHAT_PROVIDER` to choose provider.
- Test fixtures use factory-boy (`tests/helpers.py`): `UserFactory`, `ChatModelFactory`, `AiModelApiFactory`, `OrganizationFactory`, `TeamFactory`, `TeamMembershipFactory`, etc.
- `conftest.py` provides `client` (with auth), `chat_client` (without auth), and `search_config` fixtures

## Code Style

- **Formatter/Linter**: ruff (line-length 120, double quotes, space indent)
- **Imports**: isort via ruff, `apollos` as first-party
- **Pre-commit hooks**: ruff-check with autofix, ruff-format, end-of-file-fixer, trailing-whitespace, prettier for web files
- **Type checking**: mypy (runs on pre-push, not pre-commit)
- **Django settings module**: `apollos.app.settings`
- **Custom user model**: `database.ApollosUser`

## Docker

```bash
# Full stack (db + search + sandbox + server)
docker compose up

# Just the database for local dev
docker compose up database
```

Server port: 42110. Database: pgvector/pgvector:pg15. Search: SearXNG. Sandbox: Terrarium.

## Gotchas

- **`routers/helpers.py` (~2400 lines)**: Never do broad find-replace in this file. It contains identifiers like `starlette`, `pydantic`, `ClientApplication`, `Conversation` etc. that can be corrupted by substring matching. Always make surgical, targeted edits.
- **Domain convention**: All URLs use `*.apollosai.dev`. Domain is configurable via env vars (see below). Hardcoded references have `NOTE` comments with forking instructions.
- **Documentation MDX files**: Uses Docusaurus with MDX. Tags like `<TabItem>` and `<Tabs>` must use proper JSX closing (`</TabItem>`), never self-closing (`<TabItem />`). Batch operations on docs must include both `*.md` and `*.mdx` files.
- **Multiple Dockerfiles**: `.devcontainer/Dockerfile`, `Dockerfile`, `prod.Dockerfile`, `computer.Dockerfile`, `src/telemetry/Dockerfile`. Lint with `docker run --rm -i hadolint/hadolint < <file>`.
- **ESLint `next/babel` errors**: IDE-only issue when workspace root is the monorepo instead of `src/interface/web/`. Not a code bug.
- **Bootstrap config files use `.jsonc` extension**: IDEs validate `.json` strictly and flag JSONC features (comments, trailing commas) as errors. Always use `.jsonc` for config files with comments.
- **Documentation layers**: When completing features, update all layers: `CLAUDE.md` (git-tracked), auto-memory `MEMORY.md` (session-persistent), Serena memories (`project-architecture`, `codebase-navigation`). Stale docs across layers cause confusion in future sessions.

## Environment Variables (Domain & Email)

Domain and email addresses are configurable via environment variables. See `.env.example` (root) and `src/interface/web/.env.example` (frontend) for full lists.

**Backend (Python)**:
- `APOLLOS_DOMAIN` — Base domain, default `apollosai.dev`. Read via `django.conf.settings.APOLLOS_DOMAIN`. Used in CORS origins (`main.py`), rate limit messages (`helpers.py`), and email templates.
- `APOLLOS_SUPPORT_EMAIL` — Support email, default `placeholder@apollosai.dev`. Used in error messages (`configure.py`) and email templates (`email.py`).

**Frontend (Next.js)**:
- `NEXT_PUBLIC_APOLLOS_DOMAIN` — Base domain, default `apollosai.dev`. Centralized in `src/interface/web/app/common/config.ts`.
- `NEXT_PUBLIC_SUPPORT_EMAIL` — Support email. Used in error/contact messages across settings, automations, and chat pages.

**Forking**: Files where env vars aren't practical (LLM prompts, documentation, Obsidian configs) contain `NOTE` comments instructing forkers to search for `apollosai.dev` and replace with their domain.

## Environment Variables (Model Configuration)

Model providers, chat model lists, embedding config, and server chat slots are all configurable via environment variables. See `.env.example` for full documentation.

**Embedding Model** (Phase 1):
- `APOLLOS_EMBEDDING_MODEL` — Bi-encoder model name (default: `thenlper/gte-small`)
- `APOLLOS_EMBEDDING_DIMENSIONS` — Embedding vector dimensions (OpenAI `text-embedding-3-*` only)
- `APOLLOS_EMBEDDING_API_TYPE` — `local` | `openai` | `huggingface`
- `APOLLOS_EMBEDDING_API_KEY` — API key for remote embedding inference
- `APOLLOS_EMBEDDING_ENDPOINT` — Custom API URL for embedding inference
- `APOLLOS_CROSS_ENCODER_MODEL` — Cross-encoder reranking model name

**Chat Model Lists** (Phase 2) — evaluated at module import time in `utils/constants.py`:
- `APOLLOS_OPENAI_CHAT_MODELS` — Comma-separated OpenAI models (default: `gpt-4o-mini,gpt-4.1,o3,o4-mini`)
- `APOLLOS_GEMINI_CHAT_MODELS` — Comma-separated Gemini models
- `APOLLOS_ANTHROPIC_CHAT_MODELS` — Comma-separated Anthropic models
- Empty value (`VAR=`) means "no models for this provider" (NOT fallback to defaults)

**Server Chat Slots** (Phase 3):
- `APOLLOS_DEFAULT_CHAT_MODEL` — Sets `chat_default` + `chat_advanced` (unless advanced is set separately)
- `APOLLOS_ADVANCED_CHAT_MODEL` — Sets `chat_advanced` slot
- `APOLLOS_THINK_FREE_FAST_MODEL` / `APOLLOS_THINK_FREE_DEEP_MODEL` — Must be FREE tier
- `APOLLOS_THINK_PAID_FAST_MODEL` / `APOLLOS_THINK_PAID_DEEP_MODEL` — Can be any tier
- Invalid model names or PriceTier violations log a warning and skip (never crash)

**Bootstrap Configuration File** (Phase 4):
- `APOLLOS_BOOTSTRAP_CONFIG` — Path to a JSONC config file for complete model setup
- Supports `${VAR_NAME}` env var interpolation, `//` and `/* */` comments, trailing commas
- Idempotent: safe to run multiple times. See plan at `.scratchpad/litellm-models/plan.md`
- Chat slot env vars (Phase 3) override bootstrap slots. Embedding/chat-list env vars only apply when no bootstrap config exists.
- Django management command: `python manage.py bootstrap_models --config bootstrap.jsonc`

**Team Model Assignment** (Phase 5):
- `Team.settings["allowed_models"]` — List of ChatModel PKs a team can access beyond global defaults
- `Team.settings["chat_default"]` — Optional per-team default model override
- User's available models = global defaults + union of all their teams' allowed models
- `GET /api/model/chat/options` filters by team for authenticated users; anonymous mode returns all models
- `POST /api/model/chat` validates selected model is in user's available set
- Admin endpoints: `GET/POST/DELETE /api/model/team/{team_slug}/models`

**Admin Model Management API** (Phase 6):
- `GET/POST /api/model/chat/defaults` — View/update ServerChatSettings slot assignments (admin-only)
- `GET /api/model/embedding` — View embedding model configuration (admin-only)
- Auth pattern: `@requires(["authenticated"])` + `require_admin(request)` from `configure.py`
- `require_admin()` checks `is_org_admin` or `is_staff` — raises HTTPException(403) if neither

**Enterprise Foundation Models**:
- `Organization` — Single org that owns the Apollos instance (name, slug, settings JSONField)
- `Team` — Teams within the org (name, slug, settings JSONField for allowed_models)
- `TeamMembership` — Maps users to teams with roles (admin, team_lead, member)
- `ApollosUser.is_org_admin` — Boolean field for org-level admin access
- Migration: `0101_organization_team_teammembership`
