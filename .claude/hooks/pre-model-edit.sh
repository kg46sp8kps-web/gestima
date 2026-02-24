#!/bin/bash
# PRE-EDIT research for model files.
# Fires BEFORE Claude edits app/models/*.py — shows all references proactively.
# Claude must read this output before starting the edit.
# Exit 0 = proceed (informational only, never blocks).

FILE="$1"

if [[ ! "$FILE" == *"app/models/"* ]] || [[ ! "$FILE" == *.py ]]; then
  exit 0
fi

if [[ "$FILE" == *"__init__"* ]] || [[ "$FILE" == *"enum"* ]]; then
  exit 0
fi

# New file — nothing to grep yet
if [ ! -f "$FILE" ]; then
  exit 0
fi

# Extract SQLAlchemy model class names (those inheriting from Base)
CLASSES=$(python3 -c "
import re, sys
try:
    content = open('$FILE').read()
    classes = re.findall(r'^class (\w+)\(Base[,)]', content, re.MULTILINE)
    print('\n'.join(classes))
except:
    sys.exit(0)
" 2>/dev/null)

if [ -z "$CLASSES" ]; then
  exit 0
fi

echo "======================================"
echo "[PRE-EDIT] Model Change Protocol — $(basename $FILE)"
echo "READ THIS before making any edit."
echo "======================================"
echo ""
echo "Classes: $(echo $CLASSES | tr '\n' ' ')"
echo ""

while IFS= read -r CLASS; do
  [ -z "$CLASS" ] && continue
  FILES_AFFECTED=$(grep -rn "\b${CLASS}\b" app/ tests/ alembic/ scripts/ --include="*.py" 2>/dev/null \
    | grep -v "^${FILE}:" \
    | grep -v "__pycache__" \
    | cut -d: -f1 | sort -u)
  FILE_COUNT=$(echo "$FILES_AFFECTED" | grep -c "[^[:space:]]" 2>/dev/null || echo 0)
  echo "  $CLASS — ${FILE_COUNT} files:"
  echo "$FILES_AFFECTED" | sed 's/^/    /'
  echo ""
done <<< "$CLASSES"

echo "NEXT: grep for the specific field you are changing:"
echo "  grep -rn \"field_name\" app/ tests/ alembic/ scripts/ --include=\"*.py\""
echo ""
echo "Then update ALL affected files in ONE pass."
echo "======================================"
exit 0
