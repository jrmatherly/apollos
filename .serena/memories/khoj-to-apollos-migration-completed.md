# Khoj → Apollos Migration — Completed 2026-02-15

## Status: COMPLETE (Phase 2 cleanup done)

All legacy "khoj" branding has been replaced with "apollos" across the entire codebase.
Domain convention: `*.apollosai.dev` — configurable via env vars.
Hardcoded domain references have `NOTE` comments with forking instructions.

## Key Decisions
- Domain: `*.apollosai.dev` (not apollos.dev)
- Email: `placeholder@apollosai.dev` (configurable via `APOLLOS_SUPPORT_EMAIL` env var)
- Android package: `dev.apollos.app` (not `dev.apollos-ai.app` — hyphens illegal in Java)
- GitHub org: `jrmatherly/apollos`
- Social: Twitter `apollos_ai`, LinkedIn `apollos-ai`

## Environment Variables (Domain & Email)
- Backend: `APOLLOS_DOMAIN` (via Django settings), `APOLLOS_SUPPORT_EMAIL`
- Frontend: `NEXT_PUBLIC_APOLLOS_DOMAIN`, `NEXT_PUBLIC_SUPPORT_EMAIL` (centralized in `config.ts`)
- Email templates: Jinja2 `{{ domain }}` / `{{ support_email }}` variables
- `.env.example` files at root and `src/interface/web/`

## Intentional "khoj" References (3)
1. `documentation/docs/clients/obsidian.md:31` — Obsidian plugin ID (`plugins?id=khoj`)
2. `documentation/docs/clients/whatsapp.md:19` — S3 asset URL (`khoj-web-bucket.s3.amazonaws.com`)
3. `documentation/docs/contributing/development.mdx:235` — Obsidian hub link (`Plugins/khoj`)

All have `<!-- NOTE -->` markers indicating they are intentional legacy references.

## Gotchas Encountered
- First migration pass used `apollos.dev` — required Phase 2 cleanup of 81 instances
- helpers.py was corrupted by an overzealous find-replace agent — had to revert and re-apply surgically
- Android Java source directory was still under `dev/khoj/app/` — moved to `dev/apollos/app/`
- `dev.apollos-ai.app` is invalid Java — must use `dev.apollos.app`
- Batch sed on docs missed `*.mdx` files — must include both `*.md` and `*.mdx`
- MDX self-closing tags (`<TabItem />`) broke Docusaurus pages — must use proper `</TabItem>`

## Plan Location
`.scratchpad/plans/2026-02-15-khoj-to-apollos-migration.md`

## Validation Results
- 0 `apollos.dev` references in code
- 0 `apollos-ai.app` references
- 3 intentional `khoj` references (all with NOTE markers)
- 0 stale DNS TODO markers — all converted to fork-friendly NOTE comments
- All Python files pass AST parse + ruff lint
- All JSON files valid
- All MDX tags balanced (verified with tag counter script)
