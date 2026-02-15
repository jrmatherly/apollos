# Khoj → Apollos Migration — Completed 2026-02-15

## Status: COMPLETE

All legacy "khoj" branding has been replaced with "apollos" across the entire codebase.
Domain convention: `*.apollosai.dev` (with TODO markers since DNS not yet configured).

## Key Decisions
- Domain: `*.apollosai.dev` (not apollos.dev)
- Email: `placeholder@apollosai.dev` (temporary, with TODOs)
- Android package: `dev.apollos.app` (not `dev.apollos-ai.app` — hyphens illegal in Java)
- GitHub org: `jrmatherly/apollos`
- Social: Twitter `apollos_ai`, LinkedIn `apollos-ai`

## Intentional "khoj" References (3)
1. `documentation/docs/clients/obsidian.md:31` — Obsidian plugin ID (`plugins?id=khoj`)
2. `documentation/docs/clients/whatsapp.md:19` — S3 asset URL (`khoj-web-bucket.s3.amazonaws.com`)
3. `documentation/docs/contributing/development.mdx:235` — Obsidian hub link (`Plugins/khoj`)

All have `<!-- TODO -->` markers for future update.

## Gotchas Encountered
- First migration pass used `apollos.dev` — required Phase 2 cleanup of 81 instances
- helpers.py was corrupted by an overzealous find-replace agent — had to revert and re-apply surgically
- Android Java source directory was still under `dev/khoj/app/` — moved to `dev/apollos/app/`
- `dev.apollos-ai.app` is invalid Java — must use `dev.apollos.app`

## Plan Location
`.scratchpad/plans/2026-02-15-khoj-to-apollos-migration.md`

## Validation Results
- 0 `apollos.dev` references
- 0 `apollos-ai.app` references
- 3 intentional `khoj` references (all with TODOs)
- 68 TODO markers for DNS/infrastructure verification
- All Python files pass AST parse + ruff lint
- All JSON files valid
