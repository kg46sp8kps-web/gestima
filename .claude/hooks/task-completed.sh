#!/bin/bash
# Hook: TaskCompleted — Quality gate before task completion
exec python3 "${CLAUDE_PROJECT_DIR:-.}/.claude/hooks/task_completed.py"
