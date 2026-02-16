# Mise Integration

## Overview
The project uses [mise-en-place](https://mise.jdx.dev) for tool version management, virtual environment auto-activation, and task automation. Configuration is in `mise.toml` at the project root.

## Managed Tools
| Tool | Version | Purpose |
|------|---------|---------|
| python | 3.12 | Backend runtime (pinned within pyproject.toml's >=3.10,<3.13 range) |
| bun | 1 | Frontend package manager and runtime (Next.js) |
| uv | latest | Fast Python package manager |

## Key Settings
- `python.uv_venv_auto = true` — uv manages the venv lifecycle
- `_.python.venv = { path = ".venv", create = true }` — auto-creates and activates venv on `cd`
- `DJANGO_SETTINGS_MODULE = "apollos.app.settings"` — set as env var automatically
- Database defaults (`POSTGRES_*`) match `docker-compose.yml` for zero-config local dev

## Task Categories (40 tasks)
- **Setup:** `setup`, `deps`, `deps:dev`, `deps:add`
- **Dev Server:** `dev`, `dev:web`, `dev:watch`
- **Docker:** `docker:up`, `docker:down`, `docker:logs`, `docker:ps`, `docker:db`, `docker:build`
- **Database:** `db:migrate`, `db:makemigrations`, `db:showmigrations`, `db:shell`, `db:reset`
- **Frontend:** `web:install`, `web:build`, `web:dev`
- **Lint/Format:** `lint`, `lint:python`, `lint:fix`, `format`, `format:check`, `typecheck`
- **Testing:** `test`, `test:unit`, `test:chat`, `test:verbose`, `test:coverage`
- **Django:** `manage`, `shell`, `admin:create`, `collectstatic`
- **CI/Quality:** `ci`, `pre-commit`, `pre-commit:run`, `clean`, `env`

## Important Notes
- `deps` task encapsulates the `openai-whisper` build workaround (pre-installs `setuptools`, uses `--no-build-isolation-package`)
- `mise.local.toml` is gitignored — use for API keys, custom DB config, personal overrides
- `mise.lock` is gitignored — not using lockfile yet (can enable with `lockfile = true` in settings)
- `db:reset` has `confirm = true` to prevent accidental data loss
- All Python commands use `uv run` to ensure venv is active

## Files
- `mise.toml` — main config (committed)
- `.gitignore` — includes `mise.local.toml` and `mise.lock`
- `pyproject.toml` — `setuptools` added as explicit dep, `no-build-isolation-package` for whisper

## New Developer Workflow
```bash
git clone https://github.com/jrmatherly/apollos && cd apollos
mise install      # Python 3.12, bun, uv
mise run setup    # deps + migrate + frontend
mise run dev      # server at :42110
```
