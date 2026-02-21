#!/bin/bash
# Validates that new Vue components are actually imported and used somewhere.
# Catches the #1 cause of "I added it but it doesn't show up" — orphan components.
# Exit 1 = warn (not block), Exit 0 = OK.

FILE="$1"

# Only check new Vue components (not edits to existing ones)
if [[ ! "$FILE" == *"frontend/src/components/"* ]] || [[ ! "$FILE" == *.vue ]]; then
  exit 0
fi

# Extract component filename without path and extension
BASENAME=$(basename "$FILE" .vue)

# Search for imports of this component in other files
IMPORTERS=$(grep -rl "$BASENAME" frontend/src/ --include='*.vue' --include='*.ts' 2>/dev/null | grep -v "$FILE" | head -5)

if [ -z "$IMPORTERS" ]; then
  echo "========================================="
  echo "WIRING WARNING: $FILE"
  echo "========================================="
  echo ""
  echo "Component '$BASENAME' is NOT imported anywhere."
  echo "This means it will NOT be visible in the application."
  echo ""
  echo "Did you forget to:"
  echo "  1. Import it in a parent component?"
  echo "  2. Add <$BASENAME /> to a parent template?"
  echo "  3. Register it in a route or window module?"
  echo ""
  echo "Search: grep -r '$BASENAME' frontend/src/ --include='*.vue'"
  echo "========================================="
  # Exit 0 (warning, not block) — could be a new component being built
  exit 0
fi

exit 0
