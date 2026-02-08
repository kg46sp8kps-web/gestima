---
name: gestima-anti-patterns
description: Known anti-patterns and their fixes for Gestima codebase (L-001 to L-049)
---

# Gestima Anti-Patterns — Quick Reference

**Full version:** `docs/reference/ANTI-PATTERNS.md`
**Hook-enforced rules:** `docs/core/RULES.md`

## BLOCKING (hook nedovolí uložit)

| Code | Name | Hook |
|------|------|------|
| L-008 | Missing Transaction (db.commit bez try/except) | validate_edit.py |
| L-009 | Missing Validation (holé typy bez Field()) | validate_edit.py |
| L-036 | Fat Component (>300 LOC) | validate_frontend.py |
| L-040 | Wrong Doc Location (.md v rootu) | validate_docs.py |
| L-042 | Hardcoded Secrets | validate_edit.py |
| L-043 | Bare except / except+pass | validate_edit.py |
| L-044 | Debug statements (print, console.log) | validate_edit.py + validate_frontend.py |
| L-049 | TypeScript `any` type | validate_frontend.py |

## CRITICAL (no hook, manual review)

| Code | Name |
|------|------|
| L-001 | JS Calculations (výpočty v JS místo Python) |
| L-015 | Validation Walkaround (změna validace místo fix data) |

## Detaily

Viz `docs/reference/ANTI-PATTERNS.md` (kompletní list s příklady)
