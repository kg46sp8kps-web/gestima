#!/bin/bash
# Shows impact of model changes: lists all files referencing this model's classes.
# Called by Claude Code hooks after editing app/models/*.py files.
# Purpose: Prevent missed updates (tests, schemas, routers, seed data, migrations).
# Exit 0 always — informational only, does not block.

FILE="$1"

# Only check model files
if [[ ! "$FILE" == *"app/models/"* ]] || [[ ! "$FILE" == *.py ]]; then
  exit 0
fi

# Skip __init__ and enums
if [[ "$FILE" == *"__init__"* ]] || [[ "$FILE" == *"enum"* ]]; then
  exit 0
fi

# Extract SQLAlchemy model class names (those inheriting from Base)
CLASSES=$(python3 -c "
import re, sys
try:
    content = open('$FILE').read()
    # Match: class Foo(Base, ...) or class Foo(Base)
    classes = re.findall(r'^class (\w+)\(Base[,)]', content, re.MULTILINE)
    print('\n'.join(classes))
except Exception as e:
    sys.exit(0)
" 2>/dev/null)

if [ -z "$CLASSES" ]; then
  exit 0
fi

echo "======================================"
echo "[MODEL IMPACT] $(basename $FILE)"
echo "Classes: $(echo $CLASSES | tr '\n' ' ')"
echo "======================================"
echo ""

TOTAL=0
while IFS= read -r CLASS; do
  [ -z "$CLASS" ] && continue
  # Find all references, exclude current file and pycache
  MATCHES=$(grep -rn "\b${CLASS}\b" app/ tests/ alembic/ scripts/ --include="*.py" 2>/dev/null \
    | grep -v "^${FILE}:" \
    | grep -v "__pycache__")
  COUNT=$(echo "$MATCHES" | grep -c "[^[:space:]]" 2>/dev/null || echo 0)
  if [ "$COUNT" -gt 0 ]; then
    TOTAL=$((TOTAL + COUNT))
    FILES_AFFECTED=$(echo "$MATCHES" | cut -d: -f1 | sort -u)
    FILE_COUNT=$(echo "$FILES_AFFECTED" | grep -c "[^[:space:]]")
    echo "  $CLASS — ${COUNT} refs in ${FILE_COUNT} files:"
    echo "$FILES_AFFECTED" | sed 's/^/    /'
    echo ""
  fi
done <<< "$CLASSES"

if [ "$TOTAL" -eq 0 ]; then
  echo "  No external references found."
  echo ""
fi

echo ">>> Verify all listed files are updated before proceeding. <<<"
echo "======================================"
exit 0
