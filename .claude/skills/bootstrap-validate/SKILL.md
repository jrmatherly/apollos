---
name: bootstrap-validate
description: Validate a bootstrap configuration file for the Apollos model config system
---

Validate a bootstrap JSON/JSONC configuration file before deployment.

## Arguments

- Path to bootstrap config file (required)

## Validation Steps

1. **Parse JSONC**: Strip `//` line comments and `/* */` block comments, then parse as JSON
2. **Check env var references**: Find all `${VAR}` patterns and verify each env var is set
3. **Validate structure**: Check for valid top-level keys: `providers`, `embedding`, `defaults`, `team_models`, `model_tiers`
4. **Validate providers**: Each entry must have `api_type` (one of: `openai`, `anthropic`, `google`) and `api_key`
5. **Validate embedding** (if present): Check `bi_encoder`, `cross_encoder`, `api_type` fields
6. **Validate defaults** (if present): Slot names must be in: `chat_default`, `chat_advanced`, `think_free_fast`, `think_free_deep`, `think_paid_fast`, `think_paid_deep`
7. **Validate team_models** (if present): Each key is a team slug, value has `allowed_models` (list of model names) and optional `chat_default`

## Apply to Database

After validation, apply the config to verify model name resolution. **This is a live operation** — it will create/update records in the database:

```bash
python src/apollos/manage.py bootstrap_models --config <path>
```

## Reference

- Schema: `src/apollos/utils/bootstrap.py` (`apply_bootstrap_config` function)
- Example env vars: `.env.example` (root)
- Management command: `src/apollos/database/management/commands/bootstrap_models.py`
