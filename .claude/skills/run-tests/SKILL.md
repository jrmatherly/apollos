---
name: run-tests
description: Run project tests with appropriate flags for the Apollos project
---

Run tests for the Apollos project.

## Arguments

- No args: Run all tests (skip chatquality)
- File path: Run specific test file
- `-k pattern`: Run tests matching pattern

## Commands

- **All tests**: `pytest -m "not chatquality" --reuse-db`
- **Single file**: `pytest tests/<file> -v --reuse-db`
- **Single test**: `pytest tests/<file>::<test> -v --reuse-db`
- **Enterprise tests only**: `pytest tests/ -k "team or org or membership or admin" -v --reuse-db`

## Prerequisites

PostgreSQL with pgvector must be running. Start with `docker compose up database` if needed.

## Environment

- `DJANGO_SETTINGS_MODULE=apollos.app.settings` (set automatically by pytest.ini)
- `--reuse-db` avoids recreating the test database on each run
- `-m "not chatquality"` skips LLM-dependent evaluation tests (require API keys)
