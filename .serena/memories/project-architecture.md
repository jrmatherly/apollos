# Apollos (formerly Khoj) - Project Architecture

## Overview
Apollos is a production-ready AI personal assistant / semantic search application ("Your Second Brain").
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

## Key Patterns
- Hybrid Django/FastAPI: Django for ORM and admin, FastAPI for API routes
- Vector search via pgvector extension in PostgreSQL
- Multi-provider LLM support with fallback/retry (tenacity)
- Document ingestion pipeline: parse → chunk → embed → store
- Authentication via authlib + Django auth
