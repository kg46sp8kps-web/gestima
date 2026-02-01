# CLAUDE.md - GESTIMA AI Rules

**Version:** 5.0 | **Lines:** 70 | **Full docs:** [docs/](docs/)

---

## MODE DETECTION (před každým úkolem)

### SINGLE AGENT ← tento chat stačí
- Typo, bug fix, single-line změna
- Otázka, vysvětlení
- 1-2 soubory
- "Rychle udělej X"

### ŠÉFÍK MODE ← multi-agent orchestrace
- Nová feature (3+ soubory)
- Backend + Frontend + Tests
- Schema/model změna
- Architektura

**Aktivace:** Řekni "Aktivuji ŠÉFÍK mode" → [docs/agents/AGENT-INSTRUCTIONS.md](docs/agents/AGENT-INSTRUCTIONS.md)

---

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

---

## STACK

```
Backend:  FastAPI + SQLAlchemy 2.0 + Pydantic v2
Frontend: Vue 3 + Pinia + TypeScript
DB:       SQLite + WAL
Tests:    pytest + Vitest
```

---

## COMMANDS

```bash
python gestima.py run|test|seed-demo
```

---

## DOCUMENTATION MAP

| Need | Location |
|------|----------|
| **Core rules** | [docs/core/RULES.md](docs/core/RULES.md) |
| **Agents** | [docs/agents/](docs/agents/) |
| **Anti-patterns** | [docs/reference/ANTI-PATTERNS.md](docs/reference/ANTI-PATTERNS.md) |
| **Design system** | [docs/reference/DESIGN-SYSTEM.md](docs/reference/DESIGN-SYSTEM.md) |
| **Architecture** | [docs/reference/ARCHITECTURE.md](docs/reference/ARCHITECTURE.md) |
| **Vision** | [docs/reference/VISION.md](docs/reference/VISION.md) |
| **Status** | [docs/status/STATUS.md](docs/status/STATUS.md) |
| **ADRs** | [docs/ADR/](docs/ADR/) |
| **Guides** | [docs/guides/](docs/guides/) |

---

**Detailní pravidla:** [docs/core/RULES.md](docs/core/RULES.md)
