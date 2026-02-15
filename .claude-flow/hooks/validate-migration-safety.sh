#!/bin/bash
# Hook: Validate Django migration safety
# Trigger: pre-command when running makemigrations or migrate
#
# Checks for potentially dangerous migration operations.

COMMAND="$1"

# Only check migration commands
if [[ ! "$COMMAND" =~ makemigrations|migrate ]]; then
  exit 0
fi

echo "🔍 Migration Safety Check..."

# Check for uncommitted model changes
MODEL_FILE="src/apollos/database/models/__init__.py"
if git diff --name-only | grep -q "$MODEL_FILE"; then
  echo "  ℹ️  Models file has uncommitted changes — migration will capture current state"
fi

# Check if there are unapplied migrations
if [[ "$COMMAND" =~ makemigrations ]]; then
  # Warn about potential issues
  echo "  📋 Pre-migration checklist:"
  echo "     ✓ New fields have defaults or null=True for existing data"
  echo "     ✓ ForeignKey deletions use on_delete (CASCADE/SET_NULL/PROTECT)"
  echo "     ✓ unique=True fields won't conflict with existing data"
  echo "     ✓ Model renames use RenameModel (not delete+create)"
fi

# Check for destructive operations in existing migration files
if [[ "$COMMAND" =~ migrate ]]; then
  LATEST_MIGRATION=$(ls -t src/apollos/database/migrations/0*.py 2>/dev/null | head -1)
  if [ -n "$LATEST_MIGRATION" ]; then
    if grep -q "RemoveField\|DeleteModel\|AlterField.*null=False" "$LATEST_MIGRATION"; then
      echo "  ⚠️  Latest migration ($LATEST_MIGRATION) contains potentially destructive operations!"
      echo "     Review before applying in production."
    fi
  fi
fi
