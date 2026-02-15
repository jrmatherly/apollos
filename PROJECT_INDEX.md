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
| **Homepage** | https://github.com/jrmatherly/apollos |
| **Docs** | https://docs.apollosai.dev |
| **Repository** | https://github.com/jrmatherly/apollos |
| **Entry Point** | `apollos.main:run` |

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
| UI Components | shadcn/ui (components.json) |

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
| pytest | Testing (+ pytest-django, pytest-asyncio, pytest-xdist) |
| mypy | Type checking |
| ruff | Linting & formatting (line-length=120, double quotes) |
| pre-commit | Git hooks |
| hatchling + hatch-vcs | Build system with VCS versioning |

---

## 3. Architecture Overview

```text
┌─────────────────────────────────────────────────────────────────┐
│                        Client Interfaces                         │
│  Web (Next.js) │ Desktop │ Obsidian │ Emacs │ Android            │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP/WS
┌────────────────────────────▼────────────────────────────────────┐
│                      FastAPI Routers                             │
│  api.py │ api_chat.py │ api_content.py │ api_agents.py │ ...    │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                     Processing Pipeline                          │
│  Conversation (OpenAI/Anthropic/Google) │ Content Processors     │
│  Tools (online_search, run_code, mcp) │ Operator (browser/CUA)  │
│  Speech │ Image │ Embeddings                                     │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                    Search & Retrieval                             │
│  text_search.py │ search_filters (date, file, word, base)       │
│  pgvector similarity search │ cross-encoder reranking            │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                   Data Layer (Django ORM)                         │
│  Models │ Adapters │ Migrations │ PostgreSQL + pgvector           │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. Directory Structure

### Root

```text
apollos/
├── src/
│   ├── apollos/              # Core Python application
│   ├── interface/            # Client interfaces (web, desktop, obsidian, emacs, android)
│   └── telemetry/            # Telemetry microservice
├── tests/                    # pytest test suite
├── documentation/            # Docusaurus documentation site
├── scripts/                  # Dev & build scripts
├── .github/workflows/        # CI/CD pipelines
├── pyproject.toml            # Python project config
├── docker-compose.yml        # Container orchestration
├── Dockerfile                # Main Docker build
├── prod.Dockerfile           # Production Docker build
├── computer.Dockerfile       # Computer-use Docker build
├── gunicorn-config.py        # Production WSGI config
└── manifest.json             # Application manifest
```

### `src/apollos/` - Core Application

#### Entry Points

| File | Purpose |
|------|---------|
| `main.py` | Application entry point - creates FastAPI app, mounts Django, CORS, scheduling |
| `configure.py` | Server initialization, route configuration, middleware, content indexing |
| `manage.py` | Django management commands |

#### `routers/` - API Endpoints (FastAPI)

| File | Endpoints | Purpose |
|------|-----------|---------|
| `api.py` | `/api/` | Core API: search, settings, user info, health check, transcribe |
| `api_chat.py` | `/api/chat/` | Chat: send/receive messages, history, sessions, titles, export, WebSocket |
| `api_content.py` | `/api/content/` | Content CRUD: upload, index, delete, GitHub/Notion integration |
| `api_agents.py` | `/api/agents/` | Agent management: create, update, delete, list |
| `api_memories.py` | `/api/memories/` | User memory: get, update, delete long-term memories |
| `api_automation.py` | `/api/automation/` | Automations: scheduled queries, CRON jobs |
| `api_model.py` | `/api/model/` | Model config: chat model, voice model, paint model selection |
| `api_phone.py` | `/api/phone/` | Phone: update, delete, OTP verification |
| `api_subscription.py` | `/api/subscription/` | Stripe subscription management |
| `auth.py` | `/auth/` | Authentication: login, logout, magic link, OAuth, token management |
| `research.py` | `/research/` | Research mode: multi-step tool-based research |
| `web_client.py` | | Web client serving |
| `helpers.py` | | Router utilities, rate limiters, chat processing, content search |
| `email.py` | | Email integration |
| `notion.py` | | Notion OAuth & sync |
| `twilio.py` | | Twilio voice/SMS integration |
| `storage.py` | | File storage endpoints |

#### `database/` - Data Layer (Django)

| Directory/File | Purpose |
|----------------|---------|
| `models/__init__.py` | All Django models (see Data Models section) |
| `adapters/__init__.py` | Database access layer with adapter classes |
| `migrations/` | Django migration files |
| `admin.py` | Django admin configuration |
| `apps.py` | Django app config |

#### `processor/` - Processing Pipeline

##### `conversation/` - LLM Chat Processing

| File | Purpose |
|------|---------|
| `prompts.py` | All system prompts and prompt templates (~40+ prompt variables) |
| `utils.py` | Chat history construction, message formatting, token counting, JSON cleaning |
| `openai/gpt.py` | OpenAI GPT chat implementation |
| `openai/utils.py` | OpenAI-specific utilities |
| `openai/whisper.py` | Whisper speech-to-text |
| `anthropic/anthropic_chat.py` | Anthropic Claude chat implementation |
| `anthropic/utils.py` | Anthropic-specific utilities |
| `google/gemini_chat.py` | Google Gemini chat implementation |
| `google/utils.py` | Gemini-specific utilities |

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
| `text_to_entries.py` | Base text-to-entries processor |

##### `tools/` - Tool Implementations

| File | Purpose |
|------|---------|
| `online_search.py` | Web search (Google, Serper, SearXNG, Exa, Firecrawl) + webpage reading |
| `run_code.py` | Code execution (E2B sandbox, Terrarium) |
| `mcp.py` | MCP (Model Context Protocol) tool integration |

##### `operator/` - Computer Use Agent

| File | Purpose |
|------|---------|
| `operator_agent_base.py` | Base operator agent class |
| `operator_agent_openai.py` | OpenAI CUA implementation |
| `operator_agent_anthropic.py` | Anthropic CUA implementation |
| `operator_agent_binary.py` | Binary operator agent |
| `operator_environment_base.py` | Base environment class |
| `operator_environment_browser.py` | Browser environment |
| `operator_environment_computer.py` | Computer environment |
| `operator_actions.py` | Operator action definitions |
| `grounding_agent.py` | UI grounding agent |
| `grounding_agent_uitars.py` | UITars grounding agent |

##### Other Processors

| File | Purpose |
|------|---------|
| `embeddings.py` | `EmbeddingsModel` and `CrossEncoderModel` classes |
| `speech/text_to_speech.py` | Text-to-speech generation |
| `image/generate.py` | Image generation |

#### `search_type/` - Search Implementation

| File | Purpose |
|------|---------|
| `text_search.py` | Core search: embedding computation, querying, reranking, deduplication |

#### `search_filter/` - Search Filters

| File | Purpose |
|------|---------|
| `base_filter.py` | Base filter class |
| `date_filter.py` | Date-based filtering |
| `file_filter.py` | File-based filtering |
| `word_filter.py` | Word/keyword filtering |

#### `utils/` - Shared Utilities

| File | Purpose |
|------|---------|
| `helpers.py` | Core helpers: `ConversationCommand` enum, device detection, LLM client factories, token counting, URL validation |
| `rawconfig.py` | Pydantic config models: `ChatRequestBody`, `SearchResponse`, `LocationData`, etc. |
| `config.py` | Application configuration |
| `constants.py` | Application constants |
| `state.py` | Application state management |
| `models.py` | Utility models |
| `initialization.py` | Initialization routines |
| `cli.py` | CLI utilities |
| `yaml.py` | YAML handling |
| `jsonl.py` | JSONL handling |

#### `app/` - Django Application Config

| File | Purpose |
|------|---------|
| `settings.py` | Django settings |
| `urls.py` | Django URL configuration |
| `asgi.py` | ASGI application |

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
│   ├── common/                 # Shared utilities
│   └── components/             # React components
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
├── components/ui/              # shadcn/ui base components
├── hooks/                      # Custom React hooks
├── lib/                        # Utility libraries
└── public/                     # Static assets
```

#### Other Interfaces

| Directory | Platform |
|-----------|----------|
| `desktop/` | Desktop application |
| `obsidian/` | Obsidian plugin |
| `emacs/` | Emacs integration |
| `android/` | Android app |

---

## 5. Data Models

### Core Entities

| Model | Purpose |
|-------|---------|
| `ApollosUser` | Extended user model |
| `GoogleUser` | Google OAuth user |
| `ApollosApiUser` | API key user |
| `ClientApplication` | Client app registration |
| `Subscription` | User subscription (Type enum) |

### Chat & Conversation

| Model | Purpose |
|-------|---------|
| `Conversation` | Chat conversation with message history |
| `PublicConversation` | Shared public conversations |
| `ChatModel` | LLM model configuration (ModelType enum) |
| `AiModelApi` | AI API credentials |
| `Agent` | AI agent configuration (privacy, style, tools, output modes) |
| `UserConversationConfig` | Per-user chat settings |

### Content & Search

| Model | Purpose |
|-------|---------|
| `Entry` | Indexed content entry (EntryType, EntrySource enums) |
| `EntryDates` | Date metadata for entries |
| `FileObject` | Uploaded file tracking |
| `SearchModelConfig` | Search model configuration |
| `DataStore` | Data store configuration |

### Integrations

| Model | Purpose |
|-------|---------|
| `NotionConfig` | Notion integration settings |
| `GithubConfig` | GitHub integration settings |
| `GithubRepoConfig` | GitHub repo configuration |
| `McpServer` | MCP server configuration |

### Configuration & System

| Model | Purpose |
|-------|---------|
| `ServerChatSettings` | Server-wide chat settings (ChatModelSlot, MemoryMode) |
| `TextToImageModelConfig` | Image generation model config |
| `SpeechToTextModelOptions` | STT model config |
| `VoiceModelOption` | Voice/TTS model config |
| `UserVoiceModelConfig` | Per-user voice settings |
| `UserTextToImageModelConfig` | Per-user image model settings |
| `WebScraper` | Web scraper configuration (WebScraperType) |
| `ProcessLock` | Distributed process locking |
| `UserRequests` | Request tracking |
| `RateLimitRecord` | Rate limiting |
| `UserMemory` | Long-term user memories |
| `ReflectiveQuestion` | Reflective question templates |

### Context Models (Pydantic)

| Model | Purpose |
|-------|---------|
| `Context` | Search context container |
| `OnlineContext` | Web search results |
| `Intent` | User intent classification |
| `TrainOfThought` | Reasoning trace |
| `ChatMessageModel` | Chat message structure |

---

## 6. Database Adapters

The adapter layer (`database/adapters/__init__.py`) provides the primary data access API:

| Adapter | Key Methods |
|---------|-------------|
| `AgentAdapters` | CRUD for agents, accessibility checks, default agent management |
| `ConversationAdapters` | Conversation CRUD, chat model management, voice/image model config, file filters, memory settings |
| `EntryAdapters` | Entry CRUD, search with embeddings, file type/source queries |
| `FileObjectAdapters` | File object CRUD, path/regex queries |
| `AutomationAdapters` | Automation CRUD, job metadata |
| `McpServerAdapters` | MCP server queries |
| `UserMemoryAdapters` | Memory CRUD, similarity search |
| `ProcessLockAdapters` | Distributed locking |
| `PublicConversationAdapters` | Public conversation management |
| `ClientApplicationAdapters` | Client app queries |

### Standalone Functions
Authentication & user management functions: `get_or_create_user`, `get_user_by_token`, `get_user_subscription_state`, `set_user_name`, `create_apollos_token`, etc.

---

## 7. API Router Summary

| Router | Mount Point | Key Endpoints |
|--------|-------------|---------------|
| `api` | `/api` | `GET /search`, `GET /settings`, `GET /health`, `POST /transcribe`, `GET /user-info` |
| `api_chat` | `/api/chat` | `GET /`, `GET /history`, `GET /sessions`, `POST /`, `WS /ws`, `GET /starters`, `POST /feedback`, `GET /export` |
| `api_content` | `/api/content` | `PUT /`, `PATCH /`, `DELETE /`, `GET /size`, `GET /types`, `GET /files`, `POST /indexer` |
| `api_agents` | `/api/agents` | `GET /`, `GET /{slug}`, `POST /`, `PATCH /`, `DELETE /` |
| `api_memories` | `/api/memories` | `GET /`, `PATCH /`, `DELETE /` |
| `api_automation` | `/api/automations` | `GET /`, `POST /`, `PUT /`, `DELETE /`, `POST /trigger` |
| `api_model` | `/api/model` | `GET /chat/options`, `GET /chat`, `POST /chat`, `POST /voice`, `POST /paint` |
| `api_phone` | `/api/phone` | `POST /`, `DELETE /`, `POST /verify` |
| `api_subscription` | `/api/subscription` | `POST /subscribe`, `POST /update` |
| `auth` | `/auth` | `GET /login`, `POST /login`, `POST /magic-link`, `GET /token`, `DELETE /token`, `POST /logout` |
| `research` | `/research` | Tool-based multi-step research execution |

---

## 8. Processing Pipeline

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

## 9. CI/CD & Infrastructure

### GitHub Workflows

| Workflow | Purpose |
|----------|---------|
| `test.yml` | Run test suite |
| `pre-commit.yml` | Linting & formatting checks |
| `dockerize.yml` | Build & push Docker images |
| `pypi.yml` | Publish to PyPI |
| `release.yml` | Release management |
| `desktop.yml` | Desktop app build |
| `build_apollos_el.yml` | Emacs package build |
| `test_apollos_el.yml` | Emacs package tests |
| `github_pages_deploy.yml` | Documentation deployment |
| `run_evals.yml` | Evaluation benchmarks |
| `dockerize_telemetry_server.yml` | Telemetry service Docker build |

### Docker

| File | Purpose |
|------|---------|
| `Dockerfile` | Standard build |
| `prod.Dockerfile` | Production optimized build |
| `computer.Dockerfile` | Computer-use agent build |
| `docker-compose.yml` | Full stack orchestration |

---

## 10. Testing

### Test Files

| File | Coverage Area |
|------|---------------|
| `test_client.py` | API client tests |
| `test_api_automation.py` | Automation API tests |
| `test_agents.py` | Agent functionality |
| `test_conversation_utils.py` | Conversation utilities |
| `test_online_chat_director.py` | Online chat integration |
| `test_online_chat_actors.py` | Chat actors |
| `test_text_search.py` | Text search functionality |
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
| `test_helpers.py` | Helper utilities |
| `test_orgnode.py` | Org-mode node parsing |
| `test_cli.py` | CLI interface |
| `tests/evals/` | Evaluation benchmarks |

### Test Configuration
- **Framework**: pytest with strict markers
- **Plugins**: pytest-django, pytest-asyncio, pytest-xdist (parallel), freezegun
- **Custom Marker**: `chatquality` - evaluates chatbot capabilities
- **Config**: `pytest.ini` at project root

---

## 11. Code Style & Conventions

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

---

## 12. Key Enums & Constants

### ConversationCommand (from `utils/helpers.py`)
Controls chat behavior: determines which tools and modes are available to the LLM.

### Agent Configuration (from `database/models`)
- `StyleColorTypes` / `StyleIconTypes` - Agent visual styling
- `PrivacyLevel` - Agent visibility (private, public, etc.)
- `InputToolOptions` - Available input tools
- `OutputModeOptions` - Output format options

### Entry Types & Sources (from `database/models`)
- `EntryType` - Content type classification
- `EntrySource` - Content origin tracking

### Chat Model Types (from `database/models`)
- `ChatModel.ModelType` - LLM provider types
- `SearchModelConfig.ModelType` / `ApiType` - Search model configuration

---

## 13. Environment & Configuration

### Key Environment Variables

| Variable | Purpose |
|----------|---------|
| `GOOGLE_SEARCH_API_KEY` | Google Search API |
| `GOOGLE_SEARCH_ENGINE_ID` | Google Custom Search Engine |
| `SERPER_DEV_API_KEY` | Serper.dev search API |
| `FIRECRAWL_API_KEY` | Firecrawl web scraping |
| `SEARXNG_URL` | SearXNG instance URL |
| `EXA_API_KEY` | Exa search API |
| `APOLLOS_DOMAIN` | Application domain |
| `NOTION_OAUTH_CLIENT_ID` | Notion OAuth |
| `NOTION_OAUTH_CLIENT_SECRET` | Notion OAuth |

### Configuration Classes
- `ServerChatSettings` - Server-wide LLM settings
- `SearchModelConfig` - Embedding model config
- `UserConversationConfig` - Per-user chat preferences
- `configure.py: initialize_server()` - Full server bootstrap

---

*Generated from codebase analysis. Last updated: 2026-02-15.*
