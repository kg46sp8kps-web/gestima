#!/bin/bash
# Wrapper: delegates to Python3 for reliable cross-platform validation
exec python3 "${CLAUDE_PROJECT_DIR:-.}/.claude/hooks/validate_docs.py"
