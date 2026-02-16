#!/bin/bash
# Hook: UserPromptSubmit
# Injected into EVERY prompt as additionalContext
# AI physically cannot skip these rules — they are part of the prompt
# Exit 0 always (never block user input)

CONTEXT="
=== GESTIMA MANDATORY WORKFLOW (Professional SW Development) ===
These rules are ENFORCED by hooks. Violations = BLOCKED automatically.

## 0. MODE AUTO-DETECTION (before anything else):
0.1 ANALYZE the task: How many files? Which stacks? Which domains?
0.2 SINGLE AGENT: 1-2 files, one stack (only backend OR only frontend), simple fix → do it yourself
0.3 CARTMAN MODE: 3+ files, backend+frontend, schema change, cross-module refactor → activate CARTMAN (Task tool with cartman agent)
0.4 User can override: 'aktivuj CARTMANA' forces multi-agent, 'udělej sám' forces single
0.5 WHEN UNCERTAIN: prefer CARTMAN — better to over-coordinate than miss files

## 1. PLANNING PHASE (before any code):
1.1 TEXT FIRST: Explain what and WHY. Non-trivial = wait for approval. (L-000)
1.2 GREP BEFORE CODE: Search for duplicates. No reinventing. (L-002)
1.3 READ BEFORE EDIT: Read the file + surrounding context. (L-004)
1.4 CHECK ADRs: If touching architecture → read docs/ADR/ first. (L-015)
1.5 ESTIMATE SCOPE: Single file? → do it. Multi-file? → list ALL affected files first.

## 2. CODING PHASE:
2.1 EDIT NOT WRITE: Edit for existing files. Write = overwrite = data loss. (L-005)
2.2 BACKEND RULES:
    - try/except/rollback on every db.commit() (L-008) [HOOK BLOCKS]
    - Field() on every Pydantic schema type (L-009) [HOOK BLOCKS]
    - No secrets/credentials in code (L-042) [HOOK BLOCKS]
    - No bare 'except:' or 'except: pass' (L-043) [HOOK BLOCKS]
    - No print()/breakpoint() in production (L-044) [HOOK BLOCKS]
    - Type hints on public functions (L-045) [HOOK WARNS]
    - Docstrings on public functions (L-048) [HOOK WARNS]
    - response_model on every endpoint (L-047) [HOOK WARNS]
    - Business logic in services/, NOT routers (L-001)
    - Audit fields on models (L-007)
2.3 FRONTEND RULES:
    - Component < 300 LOC (L-036) [HOOK BLOCKS]
    - No emoji — Lucide icons only (L-038) [HOOK BLOCKS]
    - No hardcoded colors — var(--color-*) (L-011) [HOOK BLOCKS]
    - No hardcoded font-size — var(--text-*) (L-036) [HOOK BLOCKS]
    - No console.log/debug in production (L-044) [HOOK BLOCKS]
    - No 'any' TypeScript type (L-049) [HOOK BLOCKS]
    - No duplicate CSS utilities (L-033) [HOOK BLOCKS]
    - No mixing directives with events (L-037) [HOOK BLOCKS]
    - Floating Windows modules ONLY, no new Views (UI pattern)
2.4 NO PATCHING: Fix attempt #3 failed? STOP. Debug root cause. (L-010)

## 3. VERIFICATION PHASE (before saying 'done'):
3.1 GREP VERIFY: grep to prove zero violations. Paste output as PROOF.
3.2 SYSTEMATIC: Multi-file? grep ALL → list ALL → edit ALL → verify ALL. (L-035)
3.3 TEST: Run relevant tests (pytest / vitest). Paste output.
3.4 BUILD CHECK: If frontend change → npm run build must pass.
    BANNED: 'should be OK', 'I think it works', 'probably fine'

## 4. DOCUMENTATION PHASE:
4.1 .md files ONLY in docs/ (root = README/CLAUDE/CHANGELOG only) (L-040)
4.2 New architectural pattern → ADR in docs/ADR/NNN-name.md (L-015)
4.3 Feature complete → update CHANGELOG.md
4.4 Session notes → docs/audits/ or delete (L-041)
4.5 NEVER create summary/checklist files in root

## 5. VERSION CONTROL:
5.1 Commit messages: [type]: [description] (feat/fix/refactor/docs/test/chore)
5.2 Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
5.3 NEVER commit: .env, secrets, debug code, TODO/FIXME without tracking
5.4 NEVER: git push --force, git reset --hard without explicit approval
5.5 Atomic commits: one logical change per commit

## 6. CRITICAL THINKING (anti-sycophancy):
6.1 NEVER agree just because the user insists. If you said X is bad, HOLD YOUR POSITION.
6.2 If user pushes back on your technical recommendation → explain WHY again, don't flip.
6.3 If you change your mind → explicitly state: 'I was wrong because [reason]' or 'Your argument convinced me because [specific reason]'.
6.4 NEVER: 'Great idea!' → 'Actually no.' If it was a great idea, it still is. If it wasn't, say so immediately.
6.5 When user proposes something → FIRST evaluate pros AND cons. State both BEFORE agreeing.
6.6 If you realize you're contradicting your previous statement → STOP and say: 'Wait — I'm contradicting myself. Let me reconsider.'
6.7 Prefer honest 'I'm not sure, let me check' over confident wrong answers.

## 7. BUG FIXING PROTOCOL:
6.1 Read the FULL error/traceback first
6.2 Identify ROOT CAUSE (not symptoms)
6.3 Check CLAUDE.local.md for previous occurrence
6.4 Fix the cause → verify with test → paste output
6.5 If same bug appears 2nd time → add to anti-patterns (L-XXX)

## 7. SECURITY:
7.1 No secrets in code — use os.environ / config.py (L-042) [HOOK BLOCKS]
7.2 No bare except — always specify exception type (L-043) [HOOK BLOCKS]
7.3 Validate all user input (Pydantic Field()) (L-009)
7.4 SQL injection prevention — use SQLAlchemy ORM, no raw SQL
7.5 CORS/auth configuration via config, not hardcoded

## PROGRAMMING STYLE:
- Python: async/await, type hints, docstrings, logging (not print)
- Vue: <script setup lang=\"ts\">, composables, Pinia stores
- CSS: ONLY design tokens (var(--text-*), var(--space-*), var(--color-*))
- Icons: Lucide Vue ONLY (import from 'lucide-vue-next')
- Naming: 8-digit entity IDs (ADR-017), snake_case Python, camelCase TS

=== HOOKS ACTIVE: PreToolUse hooks BLOCK violations automatically ===
=== END MANDATORY WORKFLOW ===
"

# Append learnings from previous sessions
if [ -f "CLAUDE.local.md" ]; then
    LEARNINGS=$(cat CLAUDE.local.md)
    CONTEXT="${CONTEXT}
=== PREVIOUS SESSION LEARNINGS ===
${LEARNINGS}
=== END LEARNINGS ==="
fi

# Append uncommitted changes context
UNCOMMITTED=$(git diff --name-only 2>/dev/null | head -20)
if [ -n "$UNCOMMITTED" ]; then
    CONTEXT="${CONTEXT}
=== UNCOMMITTED CHANGES ===
${UNCOMMITTED}
=== END UNCOMMITTED ==="
fi

# Output as additionalContext JSON
ESCAPED=$(echo "$CONTEXT" | python3 -c "import sys,json; print(json.dumps(sys.stdin.read()))")
echo "{\"additionalContext\": ${ESCAPED}}"

exit 0
