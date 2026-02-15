# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Summary

Apollos (formerly Khoj) is an AI personal assistant with semantic search capabilities. It uses a **hybrid Django + FastAPI** architecture: Django handles ORM, admin, auth, and migrations; FastAPI handles all API endpoints. Data is stored in PostgreSQL with pgvector for vector similarity search. The app supports multiple LLM providers (OpenAI, Anthropic, Google Gemini).

## Development Setup

```bash
# Install Python dependencies (requires Python 3.10-3.12)
uv venv && uv sync --all-extras

# Install web frontend (Next.js + Tailwind + shadcn/ui)
cd src/interface/web && bun install && bun run export

# Install pre-commit hooks
pre-commit install -t pre-push -t pre-commit

# Full setup (includes Obsidian + Desktop)
./scripts/dev_setup.sh --full
```

**Database**: Requires PostgreSQL with pgvector extension. Default connection: `localhost:5432`, user `postgres`, db `apollos`. Or use `docker compose up database` to start one. Set `USE_EMBEDDED_DB=True` for pgserver (embedded PostgreSQL for local dev).

## Common Commands

```bash
# Run the server (default port 42110)
apollos --host 0.0.0.0 --port 42110 -vv

# Run all tests (requires PostgreSQL)
pytest

# Run a single test file
pytest tests/test_helpers.py

# Run a single test
pytest tests/test_helpers.py::test_function_name -v

# Skip chat quality eval tests
pytest -m "not chatquality"

# Lint and format
ruff check --fix src/apollos/
ruff format src/apollos/

# Type check
mypy --config-file=pyproject.toml

# Django management (migrations etc.)
python src/apollos/manage.py migrate
python src/apollos/manage.py makemigrations database
```

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

```
api_chat.py (chat/chat_ws) → routers/helpers.py (process, search, tool dispatch)
  → processor/conversation/{openai,anthropic,google}/ (LLM call)
  → processor/tools/ (online_search, run_code, mcp) if tools needed
  → database/adapters (save conversation log)
  → SSE stream or WebSocket response
```

### Data Flow: Content Indexing

```
api_content.py (put_content) → processor/content/*_to_entries.py (parse)
  → text_to_entries.py (chunk) → embeddings.py (embed)
  → Entry model (store in PostgreSQL with pgvector)
```

### Search Pipeline

`search_type/text_search.py`: query embedding → pgvector similarity search → filter (date/file/word) → cross-encoder reranking → deduplicate

### Key Modules

- **`database/models/__init__.py`**: All Django models in a single file. Core entities: `ApollosUser`, `Conversation`, `Agent`, `Entry`, `ChatModel`, `FileObject`, `UserMemory`.
- **`database/adapters/__init__.py`**: All database access logic. Adapter classes (`ConversationAdapters`, `AgentAdapters`, `EntryAdapters`, etc.) provide the data access API. Many methods have both sync and async variants (prefixed with `a`).
- **`processor/conversation/prompts.py`**: All LLM prompt templates (~40+ variables). Modify here when changing AI behavior.
- **`routers/helpers.py`**: Core chat processing logic, rate limiters, tool dispatch, content search. This is the largest and most complex router helper.
- **`utils/helpers.py`**: `ConversationCommand` enum (controls chat behavior), LLM client factory functions, device detection, token counting.

### Frontend (Web)

Next.js app at `src/interface/web/`. Pages: chat, settings, agents, search, automations, share. Components in `app/components/`. UI primitives use shadcn/ui.

## Testing

- Tests require a running PostgreSQL database with pgvector
- `pytest.ini` sets `DJANGO_SETTINGS_MODULE=apollos.app.settings` and `--reuse-db`
- Chat-related tests need an LLM API key (`OPENAI_API_KEY`, `GEMINI_API_KEY`, or `ANTHROPIC_API_KEY`). Set `APOLLOS_TEST_CHAT_PROVIDER` to choose provider.
- Test fixtures use factory-boy (`tests/helpers.py`): `UserFactory`, `ChatModelFactory`, `AiModelApiFactory`, etc.
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
