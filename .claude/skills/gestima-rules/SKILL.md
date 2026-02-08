---
name: gestima-rules
description: Core blocking rules and coding standards for Gestima project
---

# Gestima Core Rules (Quick Reference)

**Full version:** `CLAUDE.md` (8 blocking rules, mode detection, UI pattern)
**Hook-enforced rules:** `docs/core/RULES.md` (9 BLOCKING + 8 WARNING + 9 PROCESS kontrol)

## 8 BLOCKING RULES

| # | Rule | Violation |
|---|------|-----------|
| 1 | **TEXT FIRST** - netriviální → návrh → schválení → tools | L-000 |
| 2 | **EDIT NOT WRITE** - Write přepisuje, Edit mění | L-005 |
| 3 | **GREP BEFORE CODE** - check duplicity | L-002 |
| 4 | **VERIFICATION** - paste grep/test output před "hotovo" | L-033 |
| 5 | **TRANSACTION** - try/except/rollback | L-008 |
| 6 | **VALIDATION** - Pydantic Field() | L-009 |
| 7 | **GENERIC-FIRST** - <300 LOC, reusable | L-036 |
| 8 | **BUILDING BLOCKS** - reusable komponenty, 1× napsat N× použít | L-039 |

**BANNED:** "mělo by být OK", "teď už to bude fungovat"

## Detaily

Viz `CLAUDE.md` a `docs/core/RULES.md`
