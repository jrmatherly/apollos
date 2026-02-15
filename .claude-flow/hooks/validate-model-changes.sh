#!/bin/bash
# Hook: Validate model changes
# Trigger: post-edit on src/apollos/database/models/__init__.py
#
# Checks common model issues before they become migration headaches.

FILE="$1"

# Only check the models file
if [[ "$FILE" != *"database/models/__init__.py" ]]; then
  exit 0
fi

echo "🔍 Model Change Validation..."

ERRORS=0

# Check for missing __str__ on new models
MODELS_WITHOUT_STR=$(python3 -c "
import re
with open('$FILE') as f:
    content = f.read()
classes = re.findall(r'class (\w+)\((?:DbBaseModel|models\.Model|AbstractUser)\)', content)
str_methods = re.findall(r'class (\w+).*?def __str__', content, re.DOTALL)
# Simple check: class names that appear in class defs but not near __str__
for c in classes:
    if c not in str_methods and c not in ['DbBaseModel']:
        print(f'  ⚠️  {c} may be missing __str__ method')
" 2>/dev/null)

if [ -n "$MODELS_WITHOUT_STR" ]; then
  echo "$MODELS_WITHOUT_STR"
fi

# Check for ForeignKey without on_delete
FK_NO_DELETE=$(grep -n "ForeignKey" "$FILE" | grep -v "on_delete" | grep -v "^#" | grep -v "import")
if [ -n "$FK_NO_DELETE" ]; then
  echo "  ❌ ForeignKey without on_delete:"
  echo "$FK_NO_DELETE"
  ERRORS=1
fi

# Check for CharField without max_length
CHAR_NO_MAX=$(grep -n "CharField()" "$FILE" | grep -v "max_length")
if [ -n "$CHAR_NO_MAX" ]; then
  echo "  ❌ CharField without max_length:"
  echo "$CHAR_NO_MAX"
  ERRORS=1
fi

# Syntax check
python3 -c "
import ast
try:
    with open('$FILE') as f:
        ast.parse(f.read())
    # Don't print success - too noisy
except SyntaxError as e:
    print(f'  ❌ Syntax error: {e}')
" 2>/dev/null

if [ $ERRORS -eq 0 ]; then
  echo "  ✅ Model changes look good"
fi
