# Apollos Architecture (Supplemental to CLAUDE.md)

Only details NOT covered in CLAUDE.md. Read CLAUDE.md first.

## Directory Quick Reference
```
src/apollos/
  main.py              # Entry point: Django init → FastAPI app → mount Django at /server
  configure.py         # Auth backend, require_admin(), middleware setup
  routers/             # FastAPI endpoints (api_chat, api_content, api_model, api_agents, research)
  database/models/     # All Django models in __init__.py
  database/adapters/   # All data access in __init__.py (adapter classes)
  processor/           # content/ (ingestion), conversation/ (LLM providers), tools/, operator/
  search_type/         # text_search.py (pgvector + cross-encoder pipeline)
  utils/               # helpers.py (ConversationCommand), constants.py, bootstrap.py, initialization.py
src/interface/web/     # Next.js frontend (shadcn/ui)
src/interface/obsidian/# Obsidian plugin
tests/                 # pytest + factory-boy (helpers.py has all factories)
documentation/         # Docusaurus site (auto-generated sidebar)
```

## Data Flow Summary
- Chat: api_chat → helpers.py → processor/conversation/{provider} → tools/ → database/adapters → SSE/WS
- Index: api_content → processor/content/*_to_entries → embeddings.py → Entry model (pgvector)
- Search: query embed → pgvector similarity → filters → cross-encoder rerank → deduplicate

## Auth Paths (in configure.py:UserAuthenticationBackend)
1. Session (web): `request.session["user"]["email"]`
2. Bearer token (API): `ApollosApiUser.token` lookup
3. Client ID+secret (WhatsApp): `ClientApplication` validation
4. Anonymous: default user when `state.anonymous_mode` is True
