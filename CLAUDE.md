# CLAUDE.md - GESTIMA AI Rules

**Version:** 6.0 | **Full docs:** [docs/](docs/)

---

## MODE DETECTION (automatické — AI rozhoduje sám)

### SINGLE AGENT ← udělej sám, nepoužívej Task tool
- Typo, bug fix, single-line změna
- Otázka, vysvětlení
- 1-2 soubory, jeden stack (jen backend NEBO jen frontend)
- "Rychle udělej X"

### CARTMAN MODE ← automaticky aktivuj multi-agent orchestraci
- Nová feature (3+ soubory)
- Backend + Frontend současně
- Schema/model změna (backend → migrace → frontend update)
- Architektura, refaktoring napříč moduly

**AUTO-DETEKCE:** AI MUSÍ sám rozhodnout režim podle úkolu. Uživatel NEMUSÍ říkat "aktivuj CARTMANA".
**Manuální override:** Uživatel může říct "aktivuj CARTMANA" nebo "udělej sám" pro přepsání auto-detekce.
**Agent definice:** [.claude/agents/](/.claude/agents/) (backend.md, frontend.md, qa.md, auditor.md, devops.md, cartman.md)
**Orchestrace:** [docs/agents/AGENT-INSTRUCTIONS.md](docs/agents/AGENT-INSTRUCTIONS.md)

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
python gestima.py dev              # Backend + Vite dev (development, :5173)
python gestima.py run              # Pouze backend (produkce, :8000)
python gestima.py test|seed-demo
```

### `seed-demo` — Kompletní seed flow (po smazání DB)

Pořadí seedování (záleží na pořadí kvůli FK vazbám):

| # | Co | Script/funkce | Počet |
|---|-----|---------------|-------|
| 1 | DB schema | `alembic upgrade head` | — |
| 2 | MaterialGroups (+ cutting data) | `scripts/seed_material_groups.py` | 9 skupin |
| 3 | PriceCategories | `scripts/seed_price_categories.py` | 43 kategorií |
| 4 | PriceTiers (Kč/kg) | `scripts/seed_price_tiers.py` | 129 stupňů (43×3) |
| 5 | MaterialNorms (Infor data) | `scripts/seed_material_norms_complete.py` | 82 norem |
| 6 | CuttingConditions (low/mid/high) | `cutting_conditions_catalog.seed_cutting_conditions_to_db()` | 288 záznamů |
| 7 | WorkCenters | `scripts/seed_work_centers.py` | pracoviště |
| 8 | MaterialItems | `scripts/seed_material_items.py` | materiály |
| 9 | Demo parts | `scripts/seed_demo_parts.py` | demo díly |
| 10 | Admin user | inline v `gestima.py` | 1 user |

**Pravidla pro seed scripty:**
- Data MUSÍ být **inline** (žádné CSV/JSON závislosti)
- MUSÍ být **idempotentní** — **UPSERT** (UPDATE existing + INSERT new). **NIKDY DELETE ALL + INSERT** (rozbije auto-increment ID → FK v child tabulkách ukazují na neexistující záznamy!)
- Data MUSÍ pocházet z **reálného Infor exportu** (ne AI-generovaná!)
- MaterialGroups seed MUSÍ obsahovat **cutting parametry** (ISO, MRR, Vc, f, penalties)
- PriceCategories seed MUSÍ synchronizovat `material_group_id` + `shape` na existujících záznamech

---

## DOCUMENTATION MAP

| Need | Location |
|------|----------|
| **Core rules** | [docs/core/RULES.md](docs/core/RULES.md) |
| **Audit framework** | [docs/core/AUDIT-FRAMEWORK.md](docs/core/AUDIT-FRAMEWORK.md) ⭐ |
| **Agent definitions** | [.claude/agents/](/.claude/agents/) |
| **Agent orchestrace** | [docs/agents/AGENT-INSTRUCTIONS.md](docs/agents/AGENT-INSTRUCTIONS.md) |
| **Anti-patterns** | [docs/reference/ANTI-PATTERNS.md](docs/reference/ANTI-PATTERNS.md) |
| **Design system** | [docs/reference/DESIGN-SYSTEM.md](docs/reference/DESIGN-SYSTEM.md) |
| **Architecture** | [docs/reference/ARCHITECTURE.md](docs/reference/ARCHITECTURE.md) |
| **Status** | [docs/status/STATUS.md](docs/status/STATUS.md) |
| **ADRs** | [docs/ADR/](docs/ADR/) |
| **Guides** | [docs/guides/README.md](docs/guides/README.md) (Drag&drop, Testing, Deployment) |

---

## ENFORCEMENT (6 vrstev automatického vynucování)

```
Dokumentace (.md) = "měl bys"  → AI MŮŽE ignorovat
Hook (exit 2)     = "MUSÍŠ"   → AI NEMŮŽE obejít
```

### Vrstva 1: Static Analysis (PreToolUse Edit/Write)

| Hook | BLOCKING rules | Scope |
|------|---------------|-------|
| `validate_edit.py` | L-008 transaction, L-009 Field(), L-042 secrets, L-043 bare except, L-044 print/debug | `app/**/*.py` |
| `validate_frontend.py` | L-036 >300 LOC, L-044 console.log, L-049 `any` type | `*.vue`, `*.ts` |
| `validate_docs.py` | L-040 docs mimo `docs/` | `*.md` |

### Vrstva 2: Version Control (PreToolUse Bash)

| Hook | Co kontroluje |
|------|---------------|
| `commit_guard.py` | Sensitive files (.env), debug v diff, commit message, CHANGELOG, Co-Authored-By |

### Vrstva 3: Definition of Done (Stop hook)

| Hook | Co kontroluje |
|------|---------------|
| `definition_of_done.py` | Testy pro změněné services/routers, migrace pro modely, build freshness, response_model |

### Vrstva 4–6: Context + Permissions + Memory

| Vrstva | Mechanism |
|--------|-----------|
| Context injection | `session-context.sh` (prompty), `inject_subagent_context.py` (subagenty) |
| Agent permissions | `disallowedTools` ve frontmatter (Auditor: no Edit/Write/Bash) |
| Persistent memory | Learning Agent → `CLAUDE.local.md` (automaticky po každé session) |

**Detaily:** [docs/core/RULES.md](docs/core/RULES.md) | **Agent pokrytí:** [docs/agents/AGENTS.md](docs/agents/AGENTS.md)

---

**Version:** 7.1 (2026-02-13)
**Enforcement:** 14 hook souborů, 6 vrstev, 26 automatických kontrol
**Detailní pravidla:** [docs/core/RULES.md](docs/core/RULES.md)
