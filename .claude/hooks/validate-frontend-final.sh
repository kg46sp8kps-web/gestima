#!/bin/bash
# Hook: Stop (SubagentStop) for frontend agent
# Agent-based verification of final output quality
# This runs as a simple command hook — outputs validation summary to stderr
# Exit 0 = allow stop, Exit 2 = block stop (continue working)

# Read stdin for stop_hook_active check
INPUT=$(cat)
STOP_ACTIVE=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('stop_hook_active', False))" 2>/dev/null)

# Prevent infinite loop
if [ "$STOP_ACTIVE" = "True" ]; then
    exit 0
fi

# Quick check: find any recently modified .vue files >300 LOC
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
VIOLATIONS=""

for file in $(find "$PROJECT_DIR/frontend/src" -name "*.vue" -newer "$PROJECT_DIR/.claude/hooks/validate-frontend-final.sh" 2>/dev/null | head -20); do
    LOC=$(wc -l < "$file" | tr -d ' ')
    if [ "$LOC" -gt 300 ]; then
        VIOLATIONS="${VIOLATIONS}\n  - $file: $LOC LOC (max 300)"
    fi
done

if [ -n "$VIOLATIONS" ]; then
    echo "{\"decision\": \"block\", \"reason\": \"Frontend violations found:${VIOLATIONS}\\nFix before completing.\"}"
    exit 0
fi

exit 0
