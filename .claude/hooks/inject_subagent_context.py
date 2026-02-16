#!/usr/bin/env python3
"""
Hook: SubagentStart — injects mandatory workflow rules into every subagent
Reads JSON from stdin, outputs JSON with additionalContext to stdout
This runs in the MAIN session when a subagent spawns (settings.json hook)

NOTE: These rules MUST stay in sync with session-context.sh
      Both are runtime injection — cannot use file references, must be inline.
      Single source of truth for rule DEFINITIONS is docs/core/RULES.md
      This file is the runtime DELIVERY mechanism.
"""
import sys
import json
import os

# Keep in sync with session-context.sh (same rules, same L-xxx codes)
MANDATORY_RULES = """
=== GESTIMA MANDATORY WORKFLOW (injected by SubagentStart hook) ===

## 0. MODE: You are a SUBAGENT. Focus on your task. Don't orchestrate.

## 1. BEFORE writing code:
1.1 TEXT FIRST: Explain what you will do. Non-trivial = wait for approval.
1.2 GREP BEFORE CODE: Search for duplicates before writing anything.
1.3 READ BEFORE EDIT: Read file first to understand context.
1.4 CHECK ADRs: If touching architecture → read docs/ADR/ first.

## 2. WHILE writing code:
2.1 EDIT NOT WRITE: Use Edit for existing files. Write = overwrite = data loss.
2.2 BACKEND BLOCKING RULES (hooks will BLOCK if violated):
    - try/except/rollback on every db.commit() (L-008)
    - Field() on every Pydantic schema type (L-009)
    - No secrets/credentials in code (L-042)
    - No bare 'except:' or 'except: pass' (L-043)
    - No print()/breakpoint() in production (L-044)
2.3 FRONTEND BLOCKING RULES (hooks will BLOCK if violated):
    - Component < 300 LOC (L-036)
    - No console.log/debug in production (L-044)
    - No 'any' TypeScript type (L-049)
    - ONLY Floating Windows modules, NOT views
2.4 NO PATCHING: 3rd fix attempt failed? STOP. Debug root cause.

## 3. AFTER writing code:
3.1 VERIFY: grep to prove zero violations. Paste output.
3.2 TEST: Run relevant tests. Paste output.
3.3 BANNED: 'should be OK', 'I think it works', 'probably fine'

## 4. DOCUMENTATION:
4.1 .md files ONLY in docs/ (root = README/CLAUDE/CHANGELOG only) (L-040)

## 5. SECURITY:
5.1 No secrets in code (L-042)
5.2 No bare except (L-043)
5.3 Validate all input with Pydantic Field() (L-009)

## 6. CRITICAL THINKING:
6.1 NEVER flip your position just because the user insists. Hold your ground.
6.2 If you change your mind, state WHY explicitly.
6.3 State pros AND cons before agreeing with a proposal.

HOOKS ARE ACTIVE: PreToolUse hooks will BLOCK violations automatically.
If a hook blocks your Edit/Write, fix the issue and try again.

=== END MANDATORY WORKFLOW ===
"""

def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    # Load session learnings
    learnings = ""
    for path in ["CLAUDE.local.md", os.path.join(os.environ.get("CLAUDE_PROJECT_DIR", "."), "CLAUDE.local.md")]:
        try:
            with open(path, 'r') as f:
                learnings = f.read()
                break
        except FileNotFoundError:
            continue

    context = MANDATORY_RULES
    if learnings:
        context += f"\n=== PREVIOUS SESSION LEARNINGS ===\n{learnings}\n=== END LEARNINGS ==="

    # Output JSON with additionalContext
    output = {
        "hookSpecificOutput": {
            "hookEventName": "SubagentStart",
            "additionalContext": context
        }
    }
    print(json.dumps(output))
    sys.exit(0)

if __name__ == '__main__':
    main()
