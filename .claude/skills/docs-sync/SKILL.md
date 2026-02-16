---
name: docs-sync
description: Synchronize documentation across CLAUDE.md, auto-memory MEMORY.md, and Serena project memories after completing a feature or architectural change.
disable-model-invocation: true
---

Synchronize all documentation layers after a feature or architectural change.

## Arguments

- Feature/change summary (required): Brief description of what was completed

## Documentation Layers

The project maintains 3 documentation layers that must stay in sync:

1. **`CLAUDE.md`** (git-tracked) — Project instructions for Claude Code sessions
2. **Auto-memory `MEMORY.md`** (`~/.claude/projects/-Users-jason-dev-apollos/memory/MEMORY.md`) — Persistent cross-session memory
3. **Serena memories** (`project-architecture`, `codebase-navigation`) — Semantic code navigation context

## Workflow

### Step 1: Determine What Changed

Review the feature/change to identify which documentation sections need updates:
- New models, adapters, or migrations → all 3 layers
- New API endpoints → CLAUDE.md (Architecture), Serena `codebase-navigation`
- New env vars → CLAUDE.md (Environment Variables), MEMORY.md
- New files/directories → Serena `codebase-navigation`
- Config system changes → all 3 layers
- Gotchas discovered → CLAUDE.md (Gotchas), MEMORY.md (Lessons Learned)

### Step 2: Update CLAUDE.md

Edit `/Users/jason/dev/apollos/CLAUDE.md` with the relevant section updates. Keep entries concise and follow the existing format.

### Step 3: Update Auto-Memory

Edit `~/.claude/projects/-Users-jason-dev-apollos/memory/MEMORY.md`. Keep under 200 lines (lines after 200 are truncated in system prompt). Update the relevant section or add a new one if needed.

### Step 4: Update Serena Memories

Use the Serena MCP `edit_memory` tool to update:
- `project-architecture` — for structural/architectural changes
- `codebase-navigation` — for new files, endpoints, or navigation paths

### Step 5: Verify Consistency

Confirm that all 3 layers agree on:
- Migration numbers (latest migration)
- Model names and relationships
- API endpoint paths
- Environment variable names
- File paths and module locations

## Rules

- Never add session-specific or in-progress details to any layer
- Keep MEMORY.md under 200 lines
- CLAUDE.md is git-tracked — changes will appear in diffs
- Serena memories persist per-project across all sessions
- If unsure whether something belongs in docs, check: "Would a future session need this?"
