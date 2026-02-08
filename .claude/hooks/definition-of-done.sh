#!/bin/bash
# Hook: Stop/SubagentStop — Definition of Done verification
# Checks that professional workflow was followed before agent completes
exec python3 "${CLAUDE_PROJECT_DIR:-.}/.claude/hooks/definition_of_done.py"
