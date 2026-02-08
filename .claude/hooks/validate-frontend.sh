#!/bin/bash
# Wrapper: delegates to Python3 for reliable cross-platform validation
# Shell script needed because Claude Code hooks expect shell commands
exec python3 "${CLAUDE_PROJECT_DIR:-.}/.claude/hooks/validate_frontend.py"
