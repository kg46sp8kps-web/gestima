#!/bin/bash
# Wrapper: injects mandatory rules into subagent context
exec python3 "${CLAUDE_PROJECT_DIR:-.}/.claude/hooks/inject_subagent_context.py"
