---
sidebar_position: 99
---

{/* NOTE: URLs reference apollosai.dev. If forking this project, update to your domain. */}

# Environment Variables

Complete reference for all environment variables used by Apollos. Variables are grouped by category and marked with their requirement level.

**Legend:**
- **Required** — must be set for the feature to work
- **Recommended** — should be set for production deployments
- **Optional** — has a sensible default; set only if you need to customize

## Core Configuration

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `APOLLOS_DOMAIN` | `apollosai.dev` | Recommended | Base domain for the application. Used in CORS origins, rate limit messages, and email templates. |
| `APOLLOS_ALLOWED_DOMAIN` | Value of `APOLLOS_DOMAIN` | Optional | Domain allowed for CSRF trusted origins. Set this if your reverse proxy uses a different domain. |
| `APOLLOS_NO_HTTPS` | `false` | Optional | Set to `true` if running without HTTPS (e.g., local dev). Affects URL scheme in redirects and cookie security. |
| `APOLLOS_DEBUG` | `false` | Optional | Enable debug mode. Increases logging verbosity. **Never enable in production.** |
| `APOLLOS_SUPPORT_EMAIL` | `support@apollosai.dev` | Optional | Support email shown in error messages and email templates. |
| `APOLLOS_TELEMETRY_DISABLE` | `false` | Optional | Set to `true` to disable telemetry collection. |

## Django

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `APOLLOS_DJANGO_SECRET_KEY` | `!secret` | **Required** (production) | Django secret key for cryptographic signing. Must be unique and unpredictable. |

**Generate a secure secret key:**

```shell
# Using Python (recommended — generates a Django-compatible key)
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# Using openssl
openssl rand -base64 50
```

## Admin Account

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `APOLLOS_ADMIN_EMAIL` | *(interactive prompt)* | Required (non-interactive) | Admin account email address. Required when running with `--non-interactive`. |
| `APOLLOS_ADMIN_PASSWORD` | *(interactive prompt)* | Required (non-interactive) | Admin account password. Required when running with `--non-interactive`. |

**Generate a secure admin password:**

```shell
openssl rand -base64 32
```

## Database (PostgreSQL)

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `POSTGRES_DB` | `apollos` | Optional | PostgreSQL database name. |
| `POSTGRES_USER` | `postgres` | Optional | PostgreSQL username. |
| `POSTGRES_PASSWORD` | `postgres` | **Recommended** | PostgreSQL password. Change from default for production. |
| `POSTGRES_HOST` | `localhost` | Optional | PostgreSQL host. Use `database` when running in Docker Compose. |
| `POSTGRES_PORT` | `5432` | Optional | PostgreSQL port. |
| `USE_EMBEDDED_DB` | `false` | Optional | Use embedded pgserver instead of external PostgreSQL. Useful for single-user local deployments. |
| `PGSERVER_DATA_DIR` | `<project_root>/pgserver_data` | Optional | Data directory for embedded pgserver. Only used when `USE_EMBEDDED_DB=true`. |

## LLM Providers

At least one LLM provider API key is required for chat functionality.

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `OPENAI_API_KEY` | *(none)* | Optional | OpenAI API key. Also used for OpenAI-compatible endpoints (Ollama, vLLM, LMStudio). |
| `OPENAI_BASE_URL` | *(none)* | Optional | Custom base URL for OpenAI-compatible API. Set to `http://host.docker.internal:11434/v1/` for Ollama in Docker. |
| `ANTHROPIC_API_KEY` | *(none)* | Optional | Anthropic API key for Claude models. |
| `GEMINI_API_KEY` | *(none)* | Optional | Google Gemini API key. |

## Embedding Model

Controls the embedding model used for semantic search. Default uses a local model (no API key needed).

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `APOLLOS_EMBEDDING_MODEL` | `thenlper/gte-small` | Optional | Bi-encoder embedding model name. |
| `APOLLOS_EMBEDDING_DIMENSIONS` | *(auto-detect)* | Optional | Embedding vector dimensions. Required for OpenAI `text-embedding-3-*` models (e.g., `1536`). |
| `APOLLOS_EMBEDDING_API_TYPE` | `local` | Optional | Embedding API type: `local`, `openai`, or `huggingface`. |
| `APOLLOS_EMBEDDING_API_KEY` | *(none)* | Conditional | API key for remote embedding. Required when `API_TYPE` is `openai` or `huggingface`. |
| `APOLLOS_EMBEDDING_ENDPOINT` | *(none)* | Optional | Custom embedding API endpoint URL. |
| `APOLLOS_CROSS_ENCODER_MODEL` | `mixedbread-ai/mxbai-rerank-xsmall-v1` | Optional | Cross-encoder model for search result reranking. |

## Chat Model Configuration

### Model Lists

Override which chat models are created on first bootstrap. Comma-separated list of model names.

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `APOLLOS_OPENAI_CHAT_MODELS` | `gpt-4o-mini,gpt-4.1,o3,o4-mini` | Optional | OpenAI chat models to create. Set to empty string to skip. |
| `APOLLOS_GEMINI_CHAT_MODELS` | `gemini-2.0-flash,gemini-2.5-flash,gemini-2.5-pro,gemini-2.5-flash-lite` | Optional | Gemini chat models to create. |
| `APOLLOS_ANTHROPIC_CHAT_MODELS` | `claude-sonnet-4-0,claude-3-5-haiku-latest` | Optional | Anthropic chat models to create. |

### Server Chat Slots

Override which model is assigned to each server-wide chat slot. Values must match an existing ChatModel name.

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `APOLLOS_DEFAULT_CHAT_MODEL` | *(none)* | Optional | Sets `chat_default` slot (and `chat_advanced` unless separately set). Must be FREE tier. |
| `APOLLOS_ADVANCED_CHAT_MODEL` | *(none)* | Optional | Sets `chat_advanced` slot. Can be any tier. |
| `APOLLOS_THINK_FREE_FAST_MODEL` | *(none)* | Optional | Sets `think_free_fast` slot. Must be FREE tier. |
| `APOLLOS_THINK_FREE_DEEP_MODEL` | *(none)* | Optional | Sets `think_free_deep` slot. Must be FREE tier. |
| `APOLLOS_THINK_PAID_FAST_MODEL` | *(none)* | Optional | Sets `think_paid_fast` slot. Can be any tier. |
| `APOLLOS_THINK_PAID_DEEP_MODEL` | *(none)* | Optional | Sets `think_paid_deep` slot. Can be any tier. |

:::warning
Slot env vars are re-applied on every server restart, overriding admin panel changes. Remove the env var to stop overriding.
:::

### Bootstrap Configuration

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `APOLLOS_BOOTSTRAP_CONFIG` | *(none)* | Optional | Path to a JSONC file defining complete model configuration. See `bootstrap.example.jsonc` for schema. Supports `${ENV_VAR}` interpolation, comments, and trailing commas. |

## Email (Resend)

Required for magic link authentication and email notifications.

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `RESEND_API_KEY` | *(none)* | Conditional | Resend API key. Required for email-based auth and notifications. |
| `RESEND_EMAIL` | `placeholder@apollosai.dev` | Optional | Sender email address (must be verified in Resend). |
| `RESEND_AUDIENCE_ID` | *(none)* | Optional | Resend audience ID for mailing list management. |

## Google OAuth

Required for Google Sign-In authentication. Either Google OAuth or Resend (magic link) must be configured for user authentication.

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `GOOGLE_CLIENT_ID` | *(none)* | Conditional | Google OAuth 2.0 client ID. |
| `GOOGLE_CLIENT_SECRET` | *(none)* | Conditional | Google OAuth 2.0 client secret. |

## Online Search

At least one search provider enables the `/search` tool in chat. SearXNG is included in the default Docker Compose stack.

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `APOLLOS_SEARXNG_URL` | *(none)* | Optional | SearXNG instance URL. Set automatically in Docker Compose. |
| `APOLLOS_SEARXNG_SECRET` | `change-this-to-a-random-secret` | Recommended (production) | Secret key used by the SearXNG container for cryptographic signing. Generate with `openssl rand -base64 32`. |
| `GOOGLE_SEARCH_API_KEY` | *(none)* | Optional | Google Custom Search JSON API key. |
| `GOOGLE_SEARCH_ENGINE_ID` | *(none)* | Optional | Google Custom Search Engine (CSE) ID. |
| `SERPER_DEV_API_KEY` | *(none)* | Optional | Serper.dev API key for Google search results. |

## Web Scraping

Optional providers for enhanced web content extraction.

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `FIRECRAWL_API_KEY` | *(none)* | Optional | Firecrawl API key for web scraping. |
| `FIRECRAWL_API_URL` | `https://api.firecrawl.dev` | Optional | Custom Firecrawl API URL (for self-hosted). |
| `EXA_API_KEY` | *(none)* | Optional | Exa (neural search) API key. |
| `EXA_API_URL` | `https://api.exa.ai` | Optional | Custom Exa API URL. |
| `OLOSTEP_API_KEY` | *(none)* | Optional | Olostep API key for web browsing. |
| `OLOSTEP_API_URL` | `https://agent.olostep.com/olostep-p2p-incomingAPI` | Optional | Custom Olostep API URL. |

## Code Execution

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `APOLLOS_TERRARIUM_URL` | *(none)* | Optional | Terrarium sandbox URL for code execution. Set automatically in Docker Compose (`http://sandbox:8080`). |
| `E2B_API_KEY` | *(none)* | Optional | E2B API key for cloud-based code sandbox. Alternative to Terrarium. |
| `E2B_TEMPLATE` | `code-interpreter-stateful` | Optional | E2B sandbox template name. |

## Computer Use / Operator

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `APOLLOS_OPERATOR_ENABLED` | `false` | Optional | Enable the Computer Use Agent (CUA). Requires Playwright. |
| `APOLLOS_OPERATOR_ITERATIONS` | `100` | Optional | Maximum iterations for operator agent actions. |
| `APOLLOS_CDP_URL` | *(none)* | Optional | Chrome DevTools Protocol URL for browser automation. |

## Notion Integration

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `NOTION_OAUTH_CLIENT_ID` | *(none)* | Conditional | Notion OAuth client ID. Required for Notion data source. |
| `NOTION_OAUTH_CLIENT_SECRET` | *(none)* | Conditional | Notion OAuth client secret. |
| `NOTION_REDIRECT_URI` | *(none)* | Conditional | Notion OAuth redirect URI. |

## Voice / Text-to-Speech

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `ELEVEN_LABS_API_KEY` | *(none)* | Optional | ElevenLabs API key for text-to-speech. Enables voice responses. |

## Payments (Stripe)

Only needed for cloud/SaaS deployments with subscription billing.

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `STRIPE_API_KEY` | *(none)* | Conditional | Stripe secret API key. |
| `STRIPE_SIGNING_SECRET` | *(none)* | Conditional | Stripe webhook signing secret. |
| `STRIPE_APOLLOS_PRODUCT_ID` | *(none)* | Conditional | Stripe product ID for the subscription plan. |
| `APOLLOS_CLOUD_SUBSCRIPTION_URL` | *(none)* | Conditional | URL to the subscription management page. |

## SMS / Phone Verification (Twilio)

Only needed for phone-based authentication (e.g., WhatsApp bot).

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `TWILIO_ACCOUNT_SID` | *(none)* | Conditional | Twilio account SID. |
| `TWILIO_AUTH_TOKEN` | *(none)* | Conditional | Twilio auth token. |
| `TWILIO_VERIFICATION_SID` | *(none)* | Conditional | Twilio Verify service SID. |

## AWS / S3 Storage

Only needed for cloud image storage.

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `AWS_ACCESS_KEY` | *(none)* | Conditional | AWS access key for S3. |
| `AWS_SECRET_KEY` | *(none)* | Conditional | AWS secret key for S3. |
| `AWS_IMAGE_UPLOAD_BUCKET` | *(none)* | Conditional | S3 bucket name for generated images. |
| `AWS_USER_UPLOADED_IMAGES_BUCKET_NAME` | *(none)* | Conditional | S3 bucket name for user-uploaded images. |

## Advanced / Debugging

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `APOLLOS_LLM_SEED` | *(none)* | Optional | Fixed seed for LLM responses. Enables deterministic output for testing. Integer value. |
| `APOLLOS_RESEARCH_ITERATIONS` | `5` | Optional | Maximum iterations for research mode deep dives. |
| `PROMPTRACE_DIR` | *(none)* | Optional | Directory path to enable prompt tracing. Logs all LLM prompts and responses for debugging. |

## Frontend (Next.js)

These variables are used by the Next.js frontend at `src/interface/web/`. They must be prefixed with `NEXT_PUBLIC_` to be available in the browser.

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `NEXT_PUBLIC_ENV` | `development` | Optional | Build environment. Set to `production` for production builds. |
| `NEXT_PUBLIC_APOLLOS_DOMAIN` | `apollosai.dev` | Optional | Domain used in frontend URLs and links. |
| `NEXT_PUBLIC_SUPPORT_EMAIL` | `support@apollosai.dev` | Optional | Support email shown in the frontend UI. |

## Docker Compose Defaults

These variables are pre-configured in `docker-compose.yml` and generally don't need to be set externally:

| Variable | Set To | Notes |
|----------|--------|-------|
| `POSTGRES_HOST` | `database` | Points to the database service |
| `APOLLOS_TERRARIUM_URL` | `http://sandbox:8080` | Points to the Terrarium container |
| `APOLLOS_SEARXNG_URL` | `http://search:8080` | Points to the SearXNG container; also sets `SEARXNG_BASE_URL` on the search service |
| `APOLLOS_SEARXNG_SECRET` | `change-this-to-a-random-secret` | Sets `SEARXNG_SECRET` on the search service |

## Quick Reference: Minimum Production Setup

For a basic production deployment, you need at minimum:

```shell
# Required
APOLLOS_DJANGO_SECRET_KEY=$(python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")
APOLLOS_ADMIN_EMAIL=admin@yourdomain.com
APOLLOS_ADMIN_PASSWORD=$(openssl rand -base64 32)
POSTGRES_PASSWORD=$(openssl rand -base64 32)

# Recommended
APOLLOS_DOMAIN=yourdomain.com
APOLLOS_ALLOWED_DOMAIN=yourdomain.com

# At least one LLM provider
OPENAI_API_KEY=sk-...
# or
ANTHROPIC_API_KEY=sk-ant-...
# or
GEMINI_API_KEY=AI...
```
