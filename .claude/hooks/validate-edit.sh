#!/bin/bash
# Hook: PreToolUse/PostToolUse for Edit/Write on Python files
# Works in BOTH main chat and subagent frontmatter
# Reads JSON from stdin (official Claude Code hook protocol)
# Exit 0 = OK, Exit 2 = block with message (stderr)
#
# RULES ENFORCED:
# L-008: Transaction handling (try/except/rollback) — BLOCKING
# L-009: Pydantic Field() validation — BLOCKING
# L-007: Audit fields on mutable models — WARNING
# L-015: No weakening of validation constraints — WARNING
# L-028: SQLite Enum handling — WARNING
# L-001: No business calculations in routers — WARNING

exec python3 "${CLAUDE_PROJECT_DIR:-.}/.claude/hooks/validate_edit.py"
