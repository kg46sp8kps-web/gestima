#!/bin/bash
# Validates backend Python files against project rules.
# Called by Claude Code hooks after editing .py files in app/.
# Exit 1 = block the edit, Exit 0 = allow.

FILE="$1"

# Only check app/ Python files
if [[ ! "$FILE" == *"app/"* ]] || [[ ! "$FILE" == *.py ]]; then
  exit 0
fi

ERRORS=""

# Check routers for auth dependencies
if [[ "$FILE" == *"routers/"* ]]; then
  # Check for endpoint definitions without auth
  ENDPOINTS=$(grep -n '@router\.\(get\|post\|put\|delete\|patch\)' "$FILE" 2>/dev/null)
  if [ -n "$ENDPOINTS" ]; then
    # Check that get_current_user or require_role is used
    HAS_AUTH=$(grep -c 'get_current_user\|require_role' "$FILE" 2>/dev/null)
    ENDPOINT_COUNT=$(echo "$ENDPOINTS" | wc -l | tr -d ' ')
    if [ "$HAS_AUTH" -lt "$ENDPOINT_COUNT" ]; then
      ERRORS="${ERRORS}\n[AUTH] Router has $ENDPOINT_COUNT endpoints but only $HAS_AUTH auth dependencies.\nEvery endpoint MUST have Depends(get_current_user) or Depends(require_role(...)).\n"
    fi
  fi

  # Check for raw db.commit() instead of safe_commit()
  RAW_COMMIT=$(grep -n 'await db\.commit()' "$FILE" 2>/dev/null | grep -v 'safe_commit' | head -5)
  if [ -n "$RAW_COMMIT" ]; then
    ERRORS="${ERRORS}\n[DB] Raw db.commit() found. Use safe_commit() from db_helpers:\n${RAW_COMMIT}\n"
  fi

  # Check for hard delete
  HARD_DELETE=$(grep -n 'await db\.delete(' "$FILE" 2>/dev/null | head -5)
  if [ -n "$HARD_DELETE" ]; then
    ERRORS="${ERRORS}\n[DELETE] Hard delete found. Use soft_delete() from db_helpers:\n${HARD_DELETE}\n"
  fi

  # Check for f-string in SQL
  FSQL=$(grep -n 'f".*SELECT\|f".*INSERT\|f".*UPDATE\|f".*DELETE\|f".*WHERE' "$FILE" 2>/dev/null | head -5)
  if [ -n "$FSQL" ]; then
    ERRORS="${ERRORS}\n[SQL] f-string in SQL query found. Use parameterized queries:\n${FSQL}\n"
  fi
fi

# Check models for AuditMixin
if [[ "$FILE" == *"models/"* ]] && [[ "$FILE" != *"__init__"* ]] && [[ "$FILE" != *"enums"* ]]; then
  HAS_CLASS=$(grep -c 'class.*Base)' "$FILE" 2>/dev/null)
  if [ "$HAS_CLASS" -gt 0 ]; then
    HAS_AUDIT=$(grep -c 'AuditMixin' "$FILE" 2>/dev/null)
    if [ "$HAS_AUDIT" -eq 0 ]; then
      ERRORS="${ERRORS}\n[MODEL] Model without AuditMixin found. Every model MUST use AuditMixin.\n"
    fi
  fi
fi

if [ -n "$ERRORS" ]; then
  echo "========================================="
  echo "BACKEND VALIDATION FAILED: $FILE"
  echo "========================================="
  echo -e "$ERRORS"
  echo "Fix these issues before proceeding."
  exit 1
fi

exit 0
