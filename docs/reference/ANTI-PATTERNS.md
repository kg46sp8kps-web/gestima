# Anti-Patterns & Lessons Learned

**Verze:** 2.0 (2026-02-17)

## Quick Reference

| ID | Problem | Rule |
|----|---------|------|
| L-001 | Business logic in JS | Python services/ only |
| L-002 | Duplicated logic | `grep` before writing new code |
| L-003 | Lost UI state | Preserve expanded/scroll state |
| L-004 | Write instead of Edit | Edit for changes, Write for new files |
| L-005 | Partial UI update | Full refresh after API call |
| L-006 | Hardcoded data | Always from API/config |
| L-007 | Missing audit fields | created_by/updated_by on every mutation |
| L-008 | No try/except | Transaction handling with rollback |
| L-009 | Pydantic without validation | `Field()` with gt, ge, max_length |
| L-010 | Patching symptoms | 3-strike rule: debug root cause |
| L-011 | CSS conflicts | DevTools → check computed styles origin |
| L-013 | Debounce race condition | Sequence counter, ignore stale responses |
| L-015 | **Weakening validation for bad data** | **Fix DATA, not validation. Read ADR first!** |
| L-016 | Regex partial match | Use `\b` word boundaries |
| L-018 | `select()` on number input | Use `v-select-on-focus` directive |
| L-019 | Debounce data loss on navigate | beforeunload warning + sync flush |
| L-020 | Module name collision | One implementation per module name |
| L-021 | Select string/number mismatch | `parseInt(selectedId, 10)` |
| L-022 | Undefined CSS variables | Verify all `var(--foo)` exist in design-system.css |
| L-023 | Poor color contrast | Never same color family (red-on-red) |
| L-024 | Teleport testing | Use `document.querySelector` |
| L-025 | textContent whitespace | Use `.trim()` |
| L-026 | Deep object equality | Use `.toEqual()`, not `.toContain()` |
| L-027 | Intl.NumberFormat spaces | Non-breaking `\u00A0` |
| L-028 | SQLite Enum broken | Use `String(X)` instead of `Enum(str, Enum)` |
| L-029 | Post-refactor orphaned code | Grep old relationships after refactor |
| L-030 | Migration duplicate index | Use `if_not_exists=True` |
| L-031 | Missing seed scripts after refactor | Update seed_* when DB schema changes |
| L-032 | Seed script validation | Run `gestima.py seed-demo` to verify |
| L-033 | Duplicate CSS utilities | ONE definition in design-system.css only |
| L-034 | Module-specific utility classes | Check design-system.css FIRST |
| L-035 | **Piece-by-piece cleanup** | **grep ALL → edit ALL → verify ALL in one pass** |
| L-036 | Hardcoded CSS values | ONLY design system tokens: `var(--text-*)`, `var(--space-*)` |
| L-037 | Mixing directives + event handlers | ONE mechanism per function, never both |
| L-038 | Emoji in production UI | Lucide icons only (professional, parametric) |
| L-039 | Building blocks not reused | Write once, use N times |
| L-040 | Doc files outside docs/ | All .md files in docs/ (except root README, CLAUDE, CHANGELOG) |
| L-041 | Session notes not cleaned | Move to docs/audits/ or delete after feature |
| L-042 | Secrets in code | No hardcoded API keys, passwords, tokens |
| L-043 | Bare except | Always specify exception type |
| L-044 | Debug output in prod | No print(), console.log in production code |
| L-049 | TypeScript `any` | Use concrete types, avoid `any` |

## Critical Patterns (detail)

### L-010: 3-Strike Rule
```
Strike 1: Quick fix (OK)
Strike 2: Doesn't work (caution)
Strike 3: STOP → debug root cause → fix cause, not symptom
```

### L-015: Never Weaken Validation
```
ValidationError? → READ relevant ADR → Is DATA wrong or VALIDATION wrong?
  Data wrong → FIX DATA
  Validation wrong → UPDATE ADR FIRST, then change validation
```

### L-035: Systematic Multi-File Changes
```
1. grep ALL affected files
2. Count total (set expectation)
3. Read ALL in one session
4. Edit ALL in one session
5. Verify: grep returns 0 matches
6. Paste verification as PROOF
```

NEVER: "fixed one file → done" or "should be OK"

---

**Full code examples for each pattern are in the codebase itself. Grep the L-XXX ID to find implementations.**
