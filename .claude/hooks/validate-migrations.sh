#!/bin/bash
# Validates Alembic migration files against project rules.
# Called by Claude Code hooks after editing alembic/versions/*.py files.
# Exit 1 = block the edit, Exit 0 = allow.

FILE="$1"

# Only check alembic migration files
if [[ ! "$FILE" == *"alembic/versions/"* ]] || [[ ! "$FILE" == *.py ]]; then
  exit 0
fi

# Extract current file's revision ID (handles variable, typed variable, and comment formats)
CURRENT_REVISION=$(python3 -c "
import re
content = open('$FILE').read()
# Try: revision = 'xxx' or revision: str = 'xxx'
m = re.search(r\"revision(?:\s*:\s*str)?\s*=\s*['\\\"](.*?)['\\\"]\", content)
if not m:
    # Fallback: Revision ID: xxx (comment/docstring format)
    m = re.search(r'Revision ID:\s*([a-f0-9A-Z_-]+)', content)
print(m.group(1) if m else '')
" 2>/dev/null)

if [ -z "$CURRENT_REVISION" ]; then
  exit 0
fi

# Check for duplicate revision IDs and print context
RESULT=$(python3 -c "
import glob, re, sys, os

current_file = os.path.abspath('$FILE')
current_rev = '$CURRENT_REVISION'

ids = {}
collision = None

for f in sorted(glob.glob('alembic/versions/*.py')):
    f_abs = os.path.abspath(f)
    content = open(f_abs).read()
    m = re.search(r\"revision(?:\s*:\s*str)?\s*=\s*['\\\"](.*?)['\\\"]\", content)
    if not m:
        m = re.search(r'Revision ID:\s*([a-f0-9A-Z_-]+)', content)
    if m:
        rev = m.group(1)
        if rev == current_rev and f_abs != current_file:
            collision = f'COLLISION: revision \"{rev}\" already exists in {f}'
        ids[rev] = f

if collision:
    print(collision)
    print()

print('Existing revision IDs:')
for rev, f in sorted(ids.items()):
    f_abs = os.path.abspath(f)
    marker = ' <-- CURRENT' if f_abs == current_file else ''
    print(f'  {rev}  ({f.split(\"/\")[-1]}){marker}')
" 2>/dev/null)

if echo "$RESULT" | grep -q "^COLLISION:"; then
  echo "========================================="
  echo "MIGRATION VALIDATION FAILED: $FILE"
  echo "========================================="
  echo "$RESULT"
  echo ""
  echo "Choose a unique revision ID before proceeding."
  exit 1
fi

echo "[MIGRATIONS] Revision ID OK: $CURRENT_REVISION"
echo "$RESULT"
exit 0
