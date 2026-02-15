#!/bin/bash
# Hook: Validate that new/modified router endpoints have auth decorators
# Trigger: post-edit on src/apollos/routers/*.py
#
# Checks that any function decorated with @router.get/post/put/patch/delete
# also has @requires("authenticated") or equivalent auth check.

FILE="$1"

# Only check router files
if [[ ! "$FILE" =~ src/apollos/routers/ ]]; then
  exit 0
fi

# Skip non-Python files
if [[ ! "$FILE" =~ \.py$ ]]; then
  exit 0
fi

# Skip helpers.py (not a router file)
if [[ "$FILE" =~ helpers\.py$ ]]; then
  exit 0
fi

# Find route decorators without auth
UNPROTECTED=$(grep -n '@.*_router\.\(get\|post\|put\|patch\|delete\)' "$FILE" | while read -r line; do
  LINE_NUM=$(echo "$line" | cut -d: -f1)
  # Check the 5 lines before this decorator for @requires or auth dependency
  START=$((LINE_NUM - 5))
  if [ $START -lt 1 ]; then START=1; fi
  CONTEXT=$(sed -n "${START},${LINE_NUM}p" "$FILE")
  if ! echo "$CONTEXT" | grep -q 'requires\|Depends.*auth\|authenticated\|anonymous_mode'; then
    echo "  ⚠️  Line $LINE_NUM: Route handler may be missing auth decorator"
  fi
done)

if [ -n "$UNPROTECTED" ]; then
  echo "🔒 Auth Check Warning in $FILE:"
  echo "$UNPROTECTED"
  echo "  → Ensure all endpoints have @requires('authenticated') or equivalent"
fi
