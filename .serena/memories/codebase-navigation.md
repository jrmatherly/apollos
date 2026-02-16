# Apollos Codebase Navigation Guide

## Quick Reference - Where to Find Things

### API Endpoints
- All routers: `src/apollos/routers/`
- Chat API: `src/apollos/routers/api_chat.py` (25+ endpoints including WebSocket)
- Content API: `src/apollos/routers/api_content.py` (indexing, CRUD)
- Router helpers & rate limiters: `src/apollos/routers/helpers.py` (large file, many utilities)

### Data Models
- All models in single file: `src/apollos/database/models/__init__.py`
- Key models: ApollosUser, Conversation, Agent, Entry, ChatModel, FileObject, UserMemory
- Adapters (data access): `src/apollos/database/adapters/__init__.py` (very large, all adapter classes)

### LLM Integration
- OpenAI: `src/apollos/processor/conversation/openai/gpt.py`
- Anthropic: `src/apollos/processor/conversation/anthropic/anthropic_chat.py`
- Google: `src/apollos/processor/conversation/google/gemini_chat.py`
- All prompts: `src/apollos/processor/conversation/prompts.py` (~40+ prompt templates)
- Chat utilities: `src/apollos/processor/conversation/utils.py`

### Search System
- Text search core: `src/apollos/search_type/text_search.py`
- Embedding models: `src/apollos/processor/embeddings.py`
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

### Frontend (Web)
- Next.js app: `src/interface/web/`
- Pages: chat, settings, agents, search, automations, share
- Components: `src/interface/web/app/components/` (20+ component directories)
- UI primitives: `src/interface/web/components/ui/` (shadcn)

### Configuration & Utilities
- Server bootstrap: `src/apollos/configure.py`
- Core helpers: `src/apollos/utils/helpers.py` (ConversationCommand enum, LLM clients)
- Pydantic configs: `src/apollos/utils/rawconfig.py`
- Django settings: `src/apollos/app/settings.py`
- Model constants: `src/apollos/utils/constants.py` (env-var-driven model lists, evaluated at import time)
- Bootstrap config: `src/apollos/utils/bootstrap.py` (JSONC loader, idempotent model/provider/slot setup)
- Server initialization: `src/apollos/utils/initialization.py` (admin user, bootstrap, chat setup, slot config)
- Bootstrap management command: `python manage.py bootstrap_models --config path/to/bootstrap.json`

### Testing
- All tests: `tests/` directory
- Test config: `pytest.ini`
- Key test areas: conversation, search, document processing, API, agents
