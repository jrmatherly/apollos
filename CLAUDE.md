# CLAUDE.md

## Project Summary

Apollos AI (forked from Khoj) — personal assistant with semantic search. Domain: `*.apollosai.dev`. **Hybrid Django + FastAPI**: Django handles ORM/admin/auth/migrations; FastAPI handles API endpoints. PostgreSQL + pgvector for vector search. Multi-provider LLM support (OpenAI, Anthropic, Google Gemini).

## Development Setup

```bash
# Recommended (mise): manages Python 3.12, bun, uv + auto-activates .venv
mise install && mise run setup && mise run dev  # server at :42110

# Manual:
uv venv && uv pip install setuptools && uv sync --all-extras --no-build-isolation-package openai-whisper
cd src/interface/web && bun install && bun run export
pre-commit install -t pre-push -t pre-commit
```

**Database**: PostgreSQL + pgvector. `docker compose up database` or `mise run docker:db`. Default: `localhost:5432/apollos`. Set `USE_EMBEDDED_DB=True` for embedded pgserver.

## Common Commands

```bash
mise run dev              # start server (:42110)
mise run test             # run all tests (needs PostgreSQL)
mise run test:unit        # skip chat quality tests
mise run lint:fix         # ruff check --fix
mise run format           # ruff format
mise run typecheck        # mypy
mise run db:migrate       # Django migrate
mise run db:makemigrations # Django makemigrations database
mise run ci               # lint + format check + unit tests
mise run manage <cmd>     # any Django management command
```

Run `mise tasks ls` for full list. Raw commands: `pytest`, `ruff check --fix src/apollos/`, `mypy --config-file=pyproject.toml`.

## Architecture

**Startup** (`src/apollos/main.py`): Django init → FastAPI app created → routes configured (`configure.py`) → Django ASGI mounted at `/server`. Import order matters (`isort:skip_file`).

**Auth** (`configure.py:UserAuthenticationBackend`): Session (web) → Bearer token (API) → Client ID+secret (WhatsApp) → Anonymous mode fallback.

**Chat flow**: `api_chat.py` → `helpers.py` (process/search/tools) → `processor/conversation/{provider}/` → `processor/tools/` → `database/adapters` → SSE/WS response.

**Indexing**: `api_content.py` → `processor/content/*_to_entries.py` → `embeddings.py` → Entry model (pgvector).

**Search**: `text_search.py` — query embed → pgvector similarity → filters → cross-encoder rerank → deduplicate.

### Key Modules

| Module | Purpose |
|--------|---------|
| `database/models/__init__.py` | All models: ApollosUser, Conversation, Agent, Entry, ChatModel, FileObject, UserMemory, Organization, Team, TeamMembership |
| `database/adapters/__init__.py` | All data access adapters. `get_available_chat_models(user)` returns team-filtered models |
| `processor/conversation/prompts.py` | All LLM prompt templates (~40+) |
| `routers/helpers.py` | Core chat logic, rate limiters, tool dispatch (~2400 lines — surgical edits only) |
| `utils/helpers.py` | ConversationCommand enum, LLM client factories, token counting |
| `utils/constants.py` | Model lists per provider (env-var-driven, evaluated at import time) |
| `utils/bootstrap.py` | JSONC config loader, idempotent model/provider/slot/team setup |
| `utils/initialization.py` | Server bootstrap sequence |

### Frontend

Next.js at `src/interface/web/`. Domain config centralized in `app/common/config.ts` — import `APP_URL`, `DOCS_URL`, etc., never hardcode. UI primitives: shadcn/ui. Docs: `documentation/` (Docusaurus, auto-generated sidebar).

## Testing

- Requires PostgreSQL + pgvector; `pytest.ini` sets `--reuse-db`
- Chat tests need LLM API key; set `APOLLOS_TEST_CHAT_PROVIDER`
- Factories in `tests/helpers.py`: UserFactory, ChatModelFactory, AiModelApiFactory, OrganizationFactory, TeamFactory, TeamMembershipFactory
- Fixtures: `client` (auth), `chat_client` (no auth), `search_config`

## Code Style

ruff (line-length 120, double quotes). isort via ruff (`apollos` first-party). Pre-commit: ruff-check+format, prettier for web. Mypy on pre-push. Django settings: `apollos.app.settings`. Custom user: `database.ApollosUser`.

## Gotchas

- **`routers/helpers.py`**: Never broad find-replace. Identifiers like `starlette`, `pydantic`, `ClientApplication` get corrupted by substring matching.
- **Domain**: `*.apollosai.dev`, configurable via env vars. Hardcoded refs have `NOTE` comments.
- **MDX**: Proper JSX closing (`</TabItem>` not `<TabItem />`). Batch ops must include `*.md` and `*.mdx`.
- **5 Dockerfiles**: `.devcontainer/`, root, `prod.`, `computer.`, `src/telemetry/`.
- **`bump_version.sh`**: 4 parallel option cases (`-p`,`-t`,`-c`,`-n`) — all need identical updates.
- **Bootstrap configs**: Use `.jsonc` extension (supports comments/trailing commas).
- **`pyproject.toml`**: `dev` extras use `"apollos[prod,local]"` — self-referencing dep resolved locally.

## Environment Variables

Full documentation in `.env.example` (root) and `src/interface/web/.env.example` (frontend).

**Domain**: `APOLLOS_DOMAIN` (backend, via Django settings), `NEXT_PUBLIC_APOLLOS_DOMAIN` (frontend). `APOLLOS_SUPPORT_EMAIL` / `NEXT_PUBLIC_SUPPORT_EMAIL`. Forking: search for `apollosai.dev` in files with `NOTE` comments.

**Model Configuration** (6-phase system — see `.env.example` for full var list):
1. **Embedding**: `APOLLOS_EMBEDDING_MODEL`, `_DIMENSIONS`, `_API_TYPE`, `_API_KEY`, `_ENDPOINT`, `APOLLOS_CROSS_ENCODER_MODEL`
2. **Chat lists**: `APOLLOS_{OPENAI,GEMINI,ANTHROPIC}_CHAT_MODELS` (comma-separated, empty = no models)
3. **Server slots**: `APOLLOS_DEFAULT_CHAT_MODEL`, `_ADVANCED_`, `_THINK_{FREE,PAID}_{FAST,DEEP}_MODEL`
4. **Bootstrap**: `APOLLOS_BOOTSTRAP_CONFIG` — JSONC with `${VAR}` interpolation, idempotent. Slot env vars override bootstrap.
5. **Teams**: `Team.settings["allowed_models"]` (ChatModel PKs). User models = global + team union.
6. **Admin API**: `GET/POST /api/model/chat/defaults`, `GET /api/model/embedding`. Auth: `@requires(["authenticated"])` + `require_admin(request)`.

**Enterprise models**: Organization, Team, TeamMembership, `ApollosUser.is_org_admin`. Migration: `0101`. Auth: `require_admin()` checks `is_org_admin` or `is_staff`.

## Docker

```bash
docker compose up           # full stack (db + search + sandbox + server)
docker compose up database  # just PostgreSQL for local dev
```

Port 42110. DB: pgvector/pgvector:pg15. Search: SearXNG. Sandbox: Terrarium.
