# Codebase Navigation (Supplemental to CLAUDE.md)

Quick file lookup for common tasks. Only paths NOT already in CLAUDE.md.

## LLM Providers
- OpenAI: `processor/conversation/openai/gpt.py`
- Anthropic: `processor/conversation/anthropic/anthropic_chat.py`
- Google: `processor/conversation/google/gemini_chat.py`
- All prompts: `processor/conversation/prompts.py`

## Tools
- Web search: `processor/tools/online_search.py` (Google, Serper, SearXNG, Exa, Firecrawl)
- Code execution: `processor/tools/run_code.py`
- MCP: `processor/tools/mcp.py`

## Operator (Computer Use)
- Base: `processor/operator/operator_agent_base.py`
- Providers: operator_agent_openai.py, operator_agent_anthropic.py
- Environments: operator_environment_browser.py, operator_environment_computer.py

## Frontend Key Files
- Model selector: `src/interface/web/app/common/modelSelector.tsx`
- Domain config: `src/interface/web/app/common/config.ts`
- Components: `src/interface/web/app/components/` (20+ dirs)
- UI primitives: `src/interface/web/components/ui/` (shadcn)

## Admin API (in api_model.py)
- `GET/POST /api/model/chat/defaults` — slot management
- `GET /api/model/embedding` — embedding config
- `GET/POST/DELETE /api/model/team/{team_slug}/models` — team models
- `GET /api/model/chat/options` — team-filtered list (anonymous gets all)
