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

## DOCUMENTATION RULES (MANDATORY!)

**PŘED vytvořením .md souboru → CHECK:**
- ✅ Je to README.md, CLAUDE.md, nebo CHANGELOG.md? → Root OK
- ❌ Jiný .md soubor? → **docs/** directory ONLY!

| Rule | Description | Violation |
|------|-------------|-----------|
| L-040 | Doc soubory POUZE v docs/ (ne v rootu!) | Bordel |
| L-041 | Session notes → cleanup po feature | Duplikace |

**Workflow:**
1. Feature implementation → temporary notes v rootu OK
2. Feature complete → ADR v docs/ADR/
3. Session notes → move to docs/audits/ OR delete
4. Root MUST stay clean (3 files only)!

---

## STACK

```
Backend:  FastAPI + SQLAlchemy 2.0 + Pydantic v2
Frontend: Vue 3 + Pinia + TypeScript
DB:       SQLite + WAL
Tests:    pytest + Vitest
```

---

## UI PATTERN

**CRITICAL:** Vyvíjíme **POUZE pro Floating Windows** systém!

```
✅ Správně: frontend/src/components/modules/*Module.vue
❌ NIKDY:   frontend/src/views/*View.vue
```

**Struktura modulu:**
- `XxxListModule.vue` - Split-pane coordinator (LEFT: list | RIGHT: detail)
- `XxxListPanel.vue` - Seznam položek + tlačítka
- `XxxDetailPanel.vue` - Detail položky

**Příklad:** QuotesListModule.vue (koordinátor) → QuoteListPanel.vue (seznam) + QuoteDetailPanel.vue (detail)

**Views jsou DEPRECATED** - používají se POUZE pro:
- Auth (LoginView.vue)
- Admin (MasterDataView.vue)
- Settings (SettingsView.vue)
- WindowsView.vue (floating windows container)

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
| **Guides** | [docs/guides/README.md](docs/guides/README.md) (Drag&drop, Testing, Deployment) |

---

**Version:** 5.1 (2026-02-02)
**Detailní pravidla:** [docs/core/RULES.md](docs/core/RULES.md)
