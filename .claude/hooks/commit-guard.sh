#!/bin/bash
# Hook: PreToolUse for Bash — Git commit quality gate
# Intercepts git commit and verifies no secrets, debug code, format compliance
exec python3 "${CLAUDE_PROJECT_DIR:-.}/.claude/hooks/commit_guard.py"
