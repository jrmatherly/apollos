# Mise Integration (Supplemental to CLAUDE.md)

Only details not covered in CLAUDE.md's mise section.

## Key Settings in mise.toml
- `python.uv_venv_auto = true` — uv manages venv lifecycle
- `_.python.venv = { path = ".venv", create = true }` — auto-creates/activates on cd
- DB defaults match docker-compose.yml for zero-config local dev
- `mise.local.toml` (gitignored) — for API keys, custom DB, personal overrides
- `mise.lock` gitignored — lockfile not enabled yet

## Deps Task Workaround
`deps` pre-installs `setuptools` then uses `--no-build-isolation-package` for openai-whisper.
