---
name: django-migration
description: Create, review, and apply Django migrations safely. Guides through makemigrations, SQL review, and migrate workflow with safety checks.
---

Create and apply Django migrations for the Apollos project.

## Arguments

- Description of model changes (optional, for context)
- `--dry-run`: Only generate and review, don't apply

## Workflow

### Step 1: Generate Migration

```bash
cd /Users/jason/dev/apollos && uv run python src/apollos/manage.py makemigrations database
```

If no changes detected, stop and report.

### Step 2: Identify New Migration

Find the new migration file in `src/apollos/database/migrations/`. It will be the highest-numbered file. Read it to verify the operations match the intended changes.

### Step 3: Review SQL

```bash
cd /Users/jason/dev/apollos && uv run python src/apollos/manage.py sqlmigrate database <migration_number>
```

Check for:
- Destructive operations (DROP TABLE, DROP COLUMN) — flag these prominently
- Missing indexes on foreign keys or frequently-queried fields
- Large table alterations that may lock the table in production
- Correct default values and null constraints

### Step 4: Apply Migration

If not `--dry-run`, apply:

```bash
cd /Users/jason/dev/apollos && uv run python src/apollos/manage.py migrate database
```

### Step 5: Verify

```bash
cd /Users/jason/dev/apollos && uv run python src/apollos/manage.py showmigrations database | tail -5
```

Confirm the new migration shows `[X]` (applied).

## Safety Rules

- Never edit existing migration files directly — always generate new ones
- If a migration needs changes, delete the unapplied migration and regenerate
- The models file is `src/apollos/database/models/__init__.py` (single file, 900+ lines)
- Migration app label is always `database` (not `apollos` or `models`)
- `AiModelApi.name` and `ChatModel.name` are NOT unique — never add unique constraints to these
