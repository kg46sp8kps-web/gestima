#!/bin/bash
# Hook: TeammateIdle — Quality gate when teammate goes idle
exec python3 "${CLAUDE_PROJECT_DIR:-.}/.claude/hooks/teammate_idle.py"
