# Apollos Project Index

> Comprehensive project documentation generated from codebase analysis.
> Apollos AI Personal Assistant & Semantic Search Platform

---

## 1. Project Overview

| Property | Value |
|----------|-------|
| **Name** | Apollos |
| **Description** | Your Second Brain - AI personal assistant with semantic search |
| **License** | AGPL-3.0-or-later |
| **Python** | 3.10 - 3.12 |
| **Homepage** | https://apollosai.dev |
| **Docs** | https://docs.apollosai.dev |
| **Repository** | https://github.com/jrmatherly/apollos |
| **Entry Point** | `apollos.main:run` |
| **Domain** | `*.apollosai.dev` (configurable via `APOLLOS_DOMAIN` env var) |

## 2. Technology Stack

### Backend

| Component | Technology | Version |
|-----------|-----------|---------|
| Web Framework (API) | FastAPI | >= 0.110.0 |
| Web Framework (ORM/Admin) | Django | 5.1.15 |
| Database | PostgreSQL + pgvector | pgvector 0.2.4 |
| ML Framework | PyTorch | 2.6.0 |
| Embeddings | sentence-transformers | 3.4.1 |
| LLM: OpenAI | openai | >= 2.0.0, < 3.0.0 |
| LLM: Anthropic | anthropic | 0.75.0 |
| LLM: Google | google-genai | 1.52.0 |
| Text Splitting | langchain-text-splitters | 0.3.11 |
| Voice/STT | openai-whisper | >= 20231117 |
| OCR | rapidocr-onnxruntime | 1.4.4 |
| PDF Processing | pymupdf | 1.24.11 |
| Auth | authlib | 1.6.5 |
| ASGI Server | uvicorn | 0.30.6 |
| Scheduling | apscheduler | ~3.10.0 |
| HTTP Client | httpx | 0.28.1 |
| MCP Protocol | mcp | >= 1.12.4 |
| Code Sandbox | e2b-code-interpreter | ~1.0.0 |

### Frontend (Web)

| Component | Technology |
|-----------|-----------|
| Framework | Next.js (TypeScript) |
| Styling | Tailwind CSS |
| Package Manager | Bun |
| UI Components | shadcn/ui (36 primitives) |
| Icons | Phosphor Icons |
| Charts/Diagrams | Excalidraw, Mermaid |
| Math | KaTeX |
| Motion | Framer Motion |

### Production Optional Dependencies

| Component | Technology |
|-----------|-----------|
| WSGI Server | gunicorn 22.0.0 |
| Payments | stripe 7.3.0 |
| SMS/Voice | twilio 8.11 |
| Cloud Storage | boto3 >= 1.34.57 |

### Dev Tooling

| Tool | Purpose |
|------|---------|
| **mise** | Tool version management, venv activation, task runner (see `mise.toml`) |
| uv | Fast Python package manager (deps, venv, lockfile) |
| pytest | Testing (+ pytest-django, pytest-asyncio, pytest-xdist) |
| factory-boy | Test data factories |
| mypy | Type checking |
| ruff | Linting & formatting (line-length=120, double quotes) |
| pre-commit | Git hooks |
| hatchling + hatch-vcs | Build system with VCS versioning |

### mise Configuration (`mise.toml`)

| Tool | Version | Notes |
|------|---------|-------|
| python | 3.12 | Pinned; pyproject.toml allows 3.10-3.12 |
| bun | 1 | Major-pinned; Next.js frontend |
| uv | latest | Python package manager |

**Auto-configured environment:**
- `.venv` auto-created and activated on `cd`
- `DJANGO_SETTINGS_MODULE=apollos.app.settings` set automatically
- Database defaults match `docker-compose.yml`

**Quick start:** `mise install && mise run setup && mise run dev`
**All tasks:** `mise tasks ls` (40 tasks across 9 categories)

---

## 3. Architecture Overview

```text
┌─────────────────────────────────────────────────────────────────┐
│                        Client Interfaces                        │
│              Web (Next.js)  │  Obsidian Plugin                  │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP/WS
┌────────────────────────────▼────────────────────────────────────┐
│                      FastAPI Routers                            │
│  api.py │ api_chat.py │ api_content.py │ api_model.py │ ...    │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                     Processing Pipeline                         │
│  Conversation (OpenAI/Anthropic/Google) │ Content Processors    │
│  Tools (online_search, run_code, mcp) │ Operator (browser/CUA) │
│  Speech │ Image │ Embeddings                                    │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                    Search & Retrieval                            │
│  text_search.py │ search_filters (date, file, word, base)      │
│  pgvector similarity search │ cross-encoder reranking           │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                   Data Layer (Django ORM)                        │
│  Models │ Adapters │ Migrations (116) │ PostgreSQL + pgvector   │
│  Enterprise: Organization │ Team │ TeamMembership               │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. Directory Structure

### Root

```text
apollos/
├── src/
│   ├── apollos/              # Core Python application (233 .py files)
│   ├── interface/
│   │   ├── web/              # Next.js frontend (11,825 .ts/.tsx files)
│   │   └── obsidian/         # Obsidian plugin
│   └── telemetry/            # Telemetry microservice
├── tests/                    # pytest test suite (28 test files)
├── documentation/            # Docusaurus documentation site (35 pages)
├── scripts/                  # Dev & build scripts
├── .github/workflows/        # CI/CD pipelines (6 active, 5 disabled)
├── .claude/                  # Claude Code config (hooks, agents, skills)
├── pyproject.toml            # Python project config
├── mise.toml                 # mise task runner config
├── bootstrap.example.jsonc   # Example bootstrap model config
├── docker-compose.yml        # Container orchestration
├── Dockerfile                # Standard build
├── prod.Dockerfile           # Production build
├── computer.Dockerfile       # Computer-use agent build
└── .mcp.json.example         # MCP server config template
```

### `src/apollos/` - Core Application

#### Entry Points

| File | Lines | Purpose |
|------|-------|---------|
| `main.py` | — | Application entry point - creates FastAPI app, mounts Django, CORS, scheduling |
| `configure.py` | — | Server initialization, route config, middleware, `require_admin()` RBAC |
| `manage.py` | — | Django management commands |

#### `routers/` - API Endpoints (FastAPI)

| File | Lines | Endpoints | Purpose |
|------|-------|-----------|---------|
| `helpers.py` | 3,453 | — | Router utilities, rate limiters, chat processing, content search |
| `api_chat.py` | 1,750 | `/api/chat/` | Chat: messages, history, sessions, titles, export, WebSocket |
| `research.py` | 706 | `/research/` | Multi-step tool-based research |
| `api_content.py` | 636 | `/api/content/` | Content CRUD: upload, index, delete, GitHub/Notion |
| `api_agents.py` | 510 | `/api/agents/` | Agent management: create, update, delete, list |
| `api_model.py` | 431 | `/api/model/` | Model config, admin defaults, team models, embedding config |
| `auth.py` | 314 | `/auth/` | Auth: login, logout, magic link, OAuth, tokens |
| `api.py` | 268 | `/api/` | Core API: search, settings, user info, health, transcribe |
| `api_automation.py` | 243 | `/api/automation/` | Automations: scheduled queries, CRON jobs |
| `web_client.py` | 160 | — | Web client serving |
| `api_subscription.py` | 149 | `/api/subscription/` | Stripe subscription management |
| `email.py` | 145 | — | Email integration (Resend, Jinja2 templates) |
| `api_memories.py` | 114 | `/api/memories/` | User memory: get, update, delete |
| `notion.py` | 89 | — | Notion OAuth & sync |
| `api_phone.py` | 86 | `/api/phone/` | Phone: update, delete, OTP verification |
| `storage.py` | 63 | — | File storage endpoints |
| `twilio.py` | — | — | Twilio voice/SMS integration |

#### `database/` - Data Layer (Django)

| File | Lines | Purpose |
|------|-------|---------|
| `models/__init__.py` | 911 | All Django models (see Data Models section) |
| `adapters/__init__.py` | 2,479 | Database access layer with adapter classes |
| `migrations/` | 116 files | Django migrations (`0001` → `0101`) |
| `management/commands/bootstrap_models.py` | — | Bootstrap model configuration from JSONC |
| `admin.py` | — | Django admin configuration |

#### `processor/` - Processing Pipeline

##### `conversation/` - LLM Chat Processing

| File | Lines | Purpose |
|------|-------|---------|
| `prompts.py` | 1,373 | All system prompts and prompt templates (~40+ variables) |
| `utils.py` | 1,283 | Chat history construction, message formatting, token counting |
| `openai/gpt.py` | 133 | OpenAI GPT chat implementation |
| `google/gemini_chat.py` | 82 | Google Gemini chat implementation |
| `anthropic/anthropic_chat.py` | 72 | Anthropic Claude chat implementation |
| `openai/whisper.py` | — | Whisper speech-to-text |

##### `content/` - Document Processors

| Module | Formats |
|--------|---------|
| `pdf/pdf_to_entries.py` | PDF documents (PyMuPDF + OCR fallback) |
| `markdown/markdown_to_entries.py` | Markdown files |
| `org_mode/org_to_entries.py` | Org-mode files |
| `plaintext/plaintext_to_entries.py` | Plain text files |
| `docx/docx_to_entries.py` | Word documents |
| `images/image_to_entries.py` | Image files (OCR) |
| `github/github_to_entries.py` | GitHub repositories |
| `notion/notion_to_entries.py` | Notion pages |
| `text_to_entries.py` | Base text-to-entries processor (chunking) |

##### `tools/` - Tool Implementations

| File | Lines | Purpose |
|------|-------|---------|
| `online_search.py` | 671 | Web search (Google, Serper, SearXNG, Exa, Firecrawl) + webpage reading |
| `run_code.py` | 348 | Code execution (E2B sandbox, Terrarium) |
| `mcp.py` | 124 | MCP (Model Context Protocol) tool integration |

##### `operator/` - Computer Use Agent

| File | Lines | Purpose |
|------|-------|---------|
| `grounding_agent_uitars.py` | 995 | UITars grounding agent |
| `operator_environment_computer.py` | 658 | Computer environment |
| `operator_agent_anthropic.py` | 635 | Anthropic CUA implementation |
| `operator_agent_openai.py` | 472 | OpenAI CUA implementation |
| `grounding_agent.py` | 412 | UI grounding agent |
| `operator_agent_binary.py` | 405 | Binary operator agent |
| `operator_environment_browser.py` | 397 | Browser environment |
| `operator_actions.py` | 197 | Operator action definitions |
| `operator_agent_base.py` | 111 | Base operator agent class |

##### Other Processors

| File | Lines | Purpose |
|------|-------|---------|
| `embeddings.py` | 156 | `EmbeddingsModel` and `CrossEncoderModel` (supports configurable dimensions) |
| `speech/text_to_speech.py` | — | Text-to-speech generation |
| `image/generate.py` | — | Image generation |

#### `search_type/` - Search Implementation

| File | Lines | Purpose |
|------|-------|---------|
| `text_search.py` | 257 | Core search: embedding, querying, reranking, deduplication |

#### `search_filter/` - Search Filters

| File | Purpose |
|------|---------|
| `base_filter.py` | Base filter class |
| `date_filter.py` | Date-based filtering |
| `file_filter.py` | File-based filtering |
| `word_filter.py` | Word/keyword filtering |

#### `utils/` - Shared Utilities

| File | Lines | Purpose |
|------|-------|---------|
| `helpers.py` | 1,252 | `ConversationCommand` enum, device detection, LLM client factories, token counting |
| `initialization.py` | 361 | Server bootstrap: admin user, bootstrap config, chat model setup, Ollama, slots |
| `bootstrap.py` | 283 | JSONC config loader, idempotent model/provider/slot/team setup |
| `rawconfig.py` | 151 | Pydantic models: `ChatRequestBody`, `SearchResponse`, `LocationData` |
| `constants.py` | 108 | Default model lists per provider (env-var-driven, evaluated at import time) |
| `config.py` | — | Application configuration |
| `state.py` | — | Application state management |
| `models.py` | — | Utility models |
| `cli.py` | — | CLI utilities |
| `yaml.py` | — | YAML handling |
| `jsonl.py` | — | JSONL handling |

---

### `src/interface/` - Client Interfaces

#### `web/` - Next.js Web Application

```text
web/
├── app/
│   ├── layout.tsx              # Root layout
│   ├── page.tsx                # Landing page
│   ├── chat/                   # Chat interface
│   ├── settings/               # Settings page
│   ├── agents/                 # Agent management
│   ├── search/                 # Search interface
│   ├── automations/            # Automation management
│   ├── share/                  # Shared conversations
│   ├── common/
│   │   ├── config.ts           # Domain config (APP_URL, DOCS_URL, ASSETS_URL, SUPPORT_EMAIL)
│   │   └── modelSelector.tsx   # Model selector component (renders server-filtered list)
│   └── components/             # 29 React component files
│       ├── chatMessage/        # Chat message rendering
│       ├── chatInputArea/      # Chat input
│       ├── chatHistory/        # Chat history display
│       ├── chatSidebar/        # Conversation sidebar
│       ├── appSidebar/         # Application sidebar
│       ├── agentCard/          # Agent cards
│       ├── referencePanel/     # Reference panel
│       ├── allConversations/   # Conversation list
│       ├── userMemory/         # Memory display
│       ├── excalidraw/         # Diagram rendering
│       ├── mermaid/            # Mermaid diagram rendering
│       ├── suggestions/        # Chat suggestions
│       ├── profileCard/        # User profile
│       ├── navMenu/            # Navigation
│       ├── loginPrompt/        # Login UI
│       ├── shareLink/          # Share functionality
│       ├── logo/               # Branding
│       ├── loading/            # Loading states
│       ├── chatWoot/           # ChatWoot integration
│       └── providers/          # React context providers
├── components/ui/              # 36 shadcn/ui base components
├── hooks/                      # Custom React hooks
├── lib/                        # Utility libraries
└── public/                     # Static assets
```

#### `obsidian/` - Obsidian Plugin

TypeScript plugin with esbuild. Package name: `apollos`. See `src/interface/obsidian/`.

---

## 5. Data Models

### Core User Entities

| Model | Purpose |
|-------|---------|
| `ApollosUser` | Extended user model (`is_org_admin` field for enterprise RBAC) |
| `GoogleUser` | Google OAuth user |
| `ApollosApiUser` | API key user |
| `ClientApplication` | Client app registration |
| `Subscription` | User subscription (Type enum) |

### Enterprise Entities (Migration 0101)

| Model | Purpose |
|-------|---------|
| `Organization` | Single org that owns the instance (name, slug, settings JSONField) |
| `Team` | Teams within org (name, slug, `settings` JSONField for `allowed_models`/`chat_default`) |
| `TeamMembership` | Maps users to teams with roles (admin, team_lead, member) |

### Chat & Conversation

| Model | Purpose |
|-------|---------|
| `Conversation` | Chat conversation with message history |
| `PublicConversation` | Shared public conversations |
| `ChatModel` | LLM model config (ModelType enum, PriceTier). **`name` is NOT unique.** |
| `AiModelApi` | AI API credentials. **`name` is NOT unique.** |
| `Agent` | AI agent config (privacy, style, tools, output modes) |
| `UserConversationConfig` | Per-user chat settings |
| `ServerChatSettings` | Server-wide chat slot assignments (ChatModelSlot, MemoryMode) |

### Content & Search

| Model | Purpose |
|-------|---------|
| `Entry` | Indexed content entry with pgvector embeddings |
| `EntryDates` | Date metadata for entries |
| `FileObject` | Uploaded file tracking |
| `SearchModelConfig` | Search model config (`bi_encoder_dimensions` for OpenAI) |
| `DataStore` | Data store configuration |

### Integrations

| Model | Purpose |
|-------|---------|
| `NotionConfig` | Notion integration settings |
| `GithubConfig` / `GithubRepoConfig` | GitHub integration |
| `McpServer` | MCP server configuration |

### System

| Model | Purpose |
|-------|---------|
| `TextToImageModelConfig` | Image generation model config |
| `SpeechToTextModelOptions` | STT model config |
| `VoiceModelOption` / `UserVoiceModelConfig` | Voice/TTS settings |
| `WebScraper` | Web scraper config (WebScraperType) |
| `ProcessLock` | Distributed process locking |
| `UserRequests` / `RateLimitRecord` | Rate limiting |
| `UserMemory` | Long-term user memories |
| `ReflectiveQuestion` | Reflective question templates |

---

## 6. Database Adapters

The adapter layer (`database/adapters/__init__.py`, 2,479 lines) provides the data access API:

| Adapter | Key Methods |
|---------|-------------|
| `AgentAdapters` | CRUD for agents, accessibility checks, default agent management |
| `ConversationAdapters` | Conversation CRUD, `get_available_chat_models(user)` (team-filtered), voice/image model config |
| `EntryAdapters` | Entry CRUD, `search_with_embeddings`, file type/source queries |
| `FileObjectAdapters` | File object CRUD, path/regex queries |
| `AutomationAdapters` | Automation CRUD, job metadata |
| `McpServerAdapters` | MCP server queries |
| `UserMemoryAdapters` | Memory CRUD, similarity search |
| `ProcessLockAdapters` | Distributed locking |
| `PublicConversationAdapters` | Public conversation management |
| `ClientApplicationAdapters` | Client app queries |

Many methods have both sync and async variants (prefixed with `a`).

---

## 7. API Endpoints

### Public APIs

| Router | Mount Point | Key Endpoints |
|--------|-------------|---------------|
| `api` | `/api` | `GET /search`, `GET /settings`, `GET /health`, `POST /transcribe`, `GET /user-info` |
| `api_chat` | `/api/chat` | `GET /`, `GET /history`, `GET /sessions`, `POST /`, `WS /ws`, `GET /starters`, `POST /feedback`, `GET /export` |
| `api_content` | `/api/content` | `PUT /`, `PATCH /`, `DELETE /`, `GET /size`, `GET /types`, `GET /files`, `POST /indexer` |
| `api_agents` | `/api/agents` | `GET /`, `GET /{slug}`, `POST /`, `PATCH /`, `DELETE /` |
| `api_memories` | `/api/memories` | `GET /`, `PATCH /`, `DELETE /` |
| `api_automation` | `/api/automations` | `GET /`, `POST /`, `PUT /`, `DELETE /`, `POST /trigger` |
| `api_model` | `/api/model` | `GET /chat/options` (team-filtered), `GET /chat`, `POST /chat`, `POST /voice`, `POST /paint` |
| `api_phone` | `/api/phone` | `POST /`, `DELETE /`, `POST /verify` |
| `api_subscription` | `/api/subscription` | `POST /subscribe`, `POST /update` |
| `auth` | `/auth` | `GET /login`, `POST /login`, `POST /magic-link`, `GET /token`, `DELETE /token`, `POST /logout` |
| `research` | `/research` | Tool-based multi-step research execution |

### Admin-Only APIs (require `is_org_admin` or `is_staff`)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/model/chat/defaults` | `GET` | View ServerChatSettings slot assignments |
| `/api/model/chat/defaults` | `POST` | Update server chat slot assignments |
| `/api/model/embedding` | `GET` | View embedding model configuration |
| `/api/model/team/{team_slug}/models` | `GET` | List team's allowed models |
| `/api/model/team/{team_slug}/models` | `POST` | Assign models to a team |
| `/api/model/team/{team_slug}/models` | `DELETE` | Remove models from a team |

Auth pattern: `@requires(["authenticated"])` + `require_admin(request)` — NOT `Depends()`.

---

## 8. Model Configuration System (6 Phases)

### Phase 1: Embedding Env Vars
`APOLLOS_EMBEDDING_MODEL`, `_DIMENSIONS`, `_API_TYPE`, `_API_KEY`, `_ENDPOINT`, `APOLLOS_CROSS_ENCODER_MODEL`

### Phase 2: Chat Model Lists (evaluated at import time in `utils/constants.py`)
`APOLLOS_OPENAI_CHAT_MODELS`, `APOLLOS_GEMINI_CHAT_MODELS`, `APOLLOS_ANTHROPIC_CHAT_MODELS`

### Phase 3: Server Chat Slots
`APOLLOS_DEFAULT_CHAT_MODEL`, `_ADVANCED_`, `_THINK_FREE_FAST_`, `_THINK_FREE_DEEP_`, `_THINK_PAID_FAST_`, `_THINK_PAID_DEEP_`

### Phase 4: Bootstrap Config File (`APOLLOS_BOOTSTRAP_CONFIG`)
JSONC format with `${VAR}` env var interpolation. Idempotent. Example: `bootstrap.example.jsonc`.
Command: `python manage.py bootstrap_models --config <path>`

### Phase 5: Team Model Assignment
`Team.settings["allowed_models"]` — list of ChatModel PKs. User's available models = global + union of team models.

### Phase 6: Admin API
`GET/POST /api/model/chat/defaults`, `GET /api/model/embedding`, team model CRUD.

**Override semantics**: Phase 3 env vars override bootstrap slots. Phases 1-2 only apply when no bootstrap config exists.

---

## 9. Processing Pipeline

### Chat Flow

```text
User Message → Router (api_chat.py)
  → helpers.py: rate limiting, command detection
  → gather_raw_query_files: attach file context
  → search_documents: vector search if needed
  → generate_online_subqueries: web search if needed
  → send_message_to_model: route to LLM provider
    → OpenAI (gpt.py) / Anthropic (anthropic_chat.py) / Google (gemini_chat.py)
  → save_to_conversation_log
  → Stream response via SSE or WebSocket
```

### Content Indexing Flow

```text
Upload → Router (api_content.py)
  → Content Processor (*_to_entries.py): parse document
  → text_to_entries.py: chunk text
  → embeddings.py: generate embeddings
  → Entry model: store in PostgreSQL with pgvector
```

### Search Flow

```text
Query → text_search.py
  → compute query embedding
  → pgvector similarity search (EntryAdapters.search_with_embeddings)
  → apply filters (date, file, word)
  → cross-encoder reranking
  → deduplicate & sort results
```

### Tool Execution

| Tool | Providers |
|------|-----------|
| Online Search | Google Search API, Serper, SearXNG, Exa, Firecrawl |
| Code Execution | E2B sandbox, Terrarium |
| MCP | Model Context Protocol servers |
| Webpage Reading | Olostep, Exa, Firecrawl, direct scraping |

---

## 10. CI/CD & Infrastructure

### GitHub Workflows (Active)

| Workflow | Purpose |
|----------|---------|
| `test.yml` | Run test suite (uses `OPENAI_API_KEY`) |
| `pre-commit.yml` | Linting & formatting checks |
| `dockerize.yml` | Build & push Docker images |
| `pypi.yml` | Publish to PyPI |
| `run_evals.yml` | Evaluation benchmarks |
| `dockerize_telemetry_server.yml` | Telemetry service Docker build |

### GitHub Workflows (Disabled)

| Workflow | Purpose | Status |
|----------|---------|--------|
| `release.yml.disabled` | Obsidian plugin release | Needs reconfiguration |
| `desktop.yml.disabled` | Desktop app build | Interface removed |
| `build_apollos_el.yml.disabled` | Emacs package build | Interface removed |
| `test_apollos_el.yml.disabled` | Emacs package tests | Interface removed |
| `github_pages_deploy.yml.disabled` | Documentation deployment | Needs reconfiguration |

### Docker (5 Dockerfiles)

| File | Purpose |
|------|---------|
| `Dockerfile` | Standard development build |
| `prod.Dockerfile` | Production optimized build |
| `computer.Dockerfile` | Computer-use agent build |
| `.devcontainer/Dockerfile` | VS Code devcontainer |
| `src/telemetry/Dockerfile` | Telemetry service |
| `docker-compose.yml` | Full stack: server, database (pgvector), search (SearXNG), sandbox (Terrarium) |

### Other Config

| File | Purpose |
|------|---------|
| `dependabot.yml` | Automated dependency updates (pip, npm, GitHub Actions) |
| `gunicorn-config.py` | Production WSGI config |

---

## 11. Testing

### Test Files (28)

| File | Coverage Area |
|------|---------------|
| `test_client.py` | API client integration |
| `test_api_automation.py` | Automation API (Google provider, skipif guards) |
| `test_agents.py` | Agent functionality |
| `test_conversation_utils.py` | Conversation utilities |
| `test_model_configuration.py` | Model config system (Phases 1-6) |
| `test_online_chat_director.py` | Online chat integration |
| `test_online_chat_actors.py` | Chat actors |
| `test_text_search.py` | Text search |
| `test_multiple_users.py` | Multi-user scenarios |
| `test_memory_settings.py` | Memory settings |
| `test_db_lock.py` | Database locking |
| `test_pdf_to_entries.py` | PDF processing |
| `test_markdown_to_entries.py` | Markdown processing |
| `test_org_to_entries.py` | Org-mode processing |
| `test_plaintext_to_entries.py` | Plaintext processing |
| `test_docx_to_entries.py` | DOCX processing |
| `test_image_to_entries.py` | Image processing |
| `test_date_filter.py` | Date filtering |
| `test_file_filter.py` | File filtering |
| `test_word_filter.py` | Word filtering |
| `test_grep_files.py` | File grep functionality |
| `test_helpers.py` | Helper utilities (provider fallback chain) |
| `test_orgnode.py` | Org-mode node parsing |
| `test_cli.py` | CLI interface |
| `evals/eval.py` | LLM evaluation benchmarks |

### Test Configuration

- **Framework**: pytest with strict markers
- **Plugins**: pytest-django, pytest-asyncio, pytest-xdist (parallel), freezegun
- **Factories**: `UserFactory`, `ChatModelFactory`, `AiModelApiFactory`, `OrganizationFactory`, `TeamFactory`, `TeamMembershipFactory` (in `tests/helpers.py`)
- **Custom Marker**: `chatquality` - evaluates chatbot capabilities (requires API key)
- **Default provider**: OpenAI (`gpt-4o-mini`), with fallback to Gemini/Anthropic
- **Config**: `pytest.ini` at project root (`--reuse-db`, `DJANGO_SETTINGS_MODULE`)

---

## 12. Claude Code Automation

### Hooks (`.claude/settings.json`)

| Hook | Type | Trigger | Purpose |
|------|------|---------|---------|
| File guard | PreToolUse | Edit\|Write | Block `.env`/`.lock` edits, warn on `helpers.py` and migrations |
| Git guard | PreToolUse | Bash | Block `reset --hard`, `push --force`, `clean -f`, `branch -D` |
| Python format | PostToolUse | Edit\|Write | Auto-run `ruff check --fix` and `ruff format` on `.py` files |
| Frontend format | PostToolUse | Edit\|Write | Auto-run `prettier --write` on `.ts/.tsx/.js/.jsx/.css` files |

### Subagents (`.claude/agents/`)

| Agent | Purpose |
|-------|---------|
| `security-reviewer.md` | RBAC enforcement, bootstrap parsing, auth flows, API security, OWASP Top 10 |
| `django-reviewer.md` | N+1 queries, model integrity, team boundary enforcement, migration safety |

### Skills (`.claude/skills/`)

| Skill | Invocation | Purpose |
|-------|------------|---------|
| `bootstrap-validate` | Both | Validate bootstrap JSONC config before deployment |
| `run-tests` | Both | Run tests with appropriate flags |
| `django-migration` | Both | Safe migration workflow: makemigrations → sqlmigrate → migrate |
| `docs-sync` | User-only | Sync CLAUDE.md + MEMORY.md + Serena memories after features |

---

## 13. Code Style & Conventions

| Setting | Value |
|---------|-------|
| Formatter | ruff |
| Line Length | 120 |
| Quote Style | Double quotes |
| Indent Style | Spaces |
| Import Order | isort via ruff, `apollos` as first-party |
| Lint Rules | E (errors), F (warnings), I (imports) |
| Ignored | E501 (line length), F405 (star imports), E402 (import order in main.py) |
| Type Checking | mypy (strict_optional=false, ignore_missing_imports) |
| Frontend | prettier, ESLint (Next.js config) |

---

## 14. Environment Variables

### Domain & Email

| Variable | Default | Purpose |
|----------|---------|---------|
| `APOLLOS_DOMAIN` | `apollosai.dev` | Base domain (backend, via `django.conf.settings`) |
| `APOLLOS_SUPPORT_EMAIL` | `placeholder@apollosai.dev` | Support email |
| `NEXT_PUBLIC_APOLLOS_DOMAIN` | `apollosai.dev` | Base domain (frontend) |
| `NEXT_PUBLIC_SUPPORT_EMAIL` | — | Support email (frontend) |

### Model Configuration

| Variable | Phase | Purpose |
|----------|-------|---------|
| `APOLLOS_EMBEDDING_MODEL` | 1 | Bi-encoder model name |
| `APOLLOS_EMBEDDING_DIMENSIONS` | 1 | Embedding vector dimensions |
| `APOLLOS_EMBEDDING_API_TYPE` | 1 | `local` \| `openai` \| `huggingface` |
| `APOLLOS_OPENAI_CHAT_MODELS` | 2 | Comma-separated OpenAI model list |
| `APOLLOS_GEMINI_CHAT_MODELS` | 2 | Comma-separated Gemini model list |
| `APOLLOS_ANTHROPIC_CHAT_MODELS` | 2 | Comma-separated Anthropic model list |
| `APOLLOS_DEFAULT_CHAT_MODEL` | 3 | Default + advanced chat slot |
| `APOLLOS_ADVANCED_CHAT_MODEL` | 3 | Advanced chat slot override |
| `APOLLOS_BOOTSTRAP_CONFIG` | 4 | Path to JSONC bootstrap config |

### External Services

| Variable | Purpose |
|----------|---------|
| `OPENAI_API_KEY` | OpenAI API (chat, embeddings, whisper) |
| `GEMINI_API_KEY` | Google Gemini API |
| `ANTHROPIC_API_KEY` | Anthropic Claude API |
| `GOOGLE_SEARCH_API_KEY` | Google Search |
| `SERPER_DEV_API_KEY` | Serper.dev search |
| `FIRECRAWL_API_KEY` | Firecrawl web scraping |
| `SEARXNG_URL` | SearXNG instance |
| `EXA_API_KEY` | Exa search |

---

*Generated from codebase analysis. Last updated: 2026-02-15.*
