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
│   ├── configure.py      # Configuration
│   ├── manage.py         # Django management
│   ├── routers/          # FastAPI API endpoints
│   │   ├── api.py        # Main API router
│   │   ├── api_chat.py   # Chat endpoints
│   │   ├── api_content.py # Content management
│   │   ├── api_agents.py # Agent endpoints
│   │   ├── api_memories.py # Memory endpoints
│   │   ├── auth.py       # Authentication
│   │   ├── research.py   # Research mode
│   │   └── ...
│   ├── database/         # Django models & migrations
│   │   ├── models/       # Data models
│   │   ├── adapters/     # Database adapters
│   │   └── migrations/   # Django migrations
│   ├── processor/        # Data processing pipeline
│   │   ├── content/      # Document processors
│   │   ├── conversation/ # Chat/conversation handling
│   │   ├── tools/        # Tool implementations
│   │   ├── operator/     # Operator logic
│   │   ├── speech/       # Voice processing
│   │   ├── image/        # Image processing
│   │   └── embeddings.py # Embedding generation
│   ├── search_type/      # Search implementations
│   ├── search_filter/    # Search filtering
│   ├── utils/            # Shared utilities
│   ├── interface/        # Web UI assets
│   └── app/              # Django app config
├── interface/            # Client interfaces
│   ├── web/              # Web frontend
│   ├── desktop/          # Desktop app
│   ├── obsidian/         # Obsidian plugin
│   ├── emacs/            # Emacs integration
│   └── android/          # Android app
└── telemetry/            # Telemetry service

tests/                    # Test suite (pytest)
documentation/            # Project docs
```

## Model Configuration System
4-phase environment variable and bootstrap configuration:
1. **Embedding env vars** (`APOLLOS_EMBEDDING_MODEL`, `_DIMENSIONS`, `_API_TYPE`, `_API_KEY`, `_ENDPOINT`, `APOLLOS_CROSS_ENCODER_MODEL`) — apply only when creating NEW SearchModelConfig records
2. **Chat model list env vars** (`APOLLOS_OPENAI_CHAT_MODELS`, `_GEMINI_`, `_ANTHROPIC_`) — evaluated at module import time in `utils/constants.py`
3. **Server chat slot env vars** (`APOLLOS_DEFAULT_CHAT_MODEL`, `_ADVANCED_`, `_THINK_FREE_FAST_`, `_THINK_FREE_DEEP_`, `_THINK_PAID_FAST_`, `_THINK_PAID_DEEP_`) — always override bootstrap slots
4. **Bootstrap config file** (`APOLLOS_BOOTSTRAP_CONFIG`) — JSONC with `${VAR}` interpolation, idempotent create/update

Key files: `utils/bootstrap.py`, `utils/constants.py`, `utils/initialization.py`, `database/management/commands/bootstrap_models.py`

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
- AiModelApi.name and ChatModel.name are NOT unique — use filter().first() pattern, not update_or_create
