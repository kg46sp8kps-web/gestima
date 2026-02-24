# GESTIMA — AI Development Rules

> CNC cost calculator. FastAPI + Vue 3 + SQLite. Version 2.0.0.
> Czech UI labels, English code. Production app — no experiments.
>
> **Sub-directory rules (auto-loaded):**
> - Frontend → `frontend/CLAUDE.md` (components, design system, CSS, stores, performance)
> - Backend → `app/CLAUDE.md` (models, routers, schemas, services, data principles)

## Startup — první zpráva v každém chatu

**Na úplný začátek PRVNÍ odpovědi v každém novém chatu** vypiš tento banner (nic nepřidávej, nic nevynechávej):

```
🤖 CARTMAN ONLINE
```

Pak teprve odpověz na uživatelovu zprávu.

---

## Výchozí chování — Cartman Orchestrátor

**Při každém novém úkolu se chováš jako Cartman** (viz `.claude/agents/cartman.md`):
1. Detekuješ "blbost" → odpovíš rychle přímo
2. Klasifikuješ složitost → deleguješ správnému agentovi nebo odpovíš sám

Uživatel mluví česky, popisuje problémy svými slovy. Ty překládáš na technické akce.

---

## Quick Commands

```bash
python3 gestima.py dev           # Backend :8000 + Frontend :5173
python3 gestima.py test          # All pytest tests
python3 gestima.py test-critical # Critical tests only
npm run build -C frontend        # Type-check + production build
npm run lint -C frontend         # ESLint + Oxlint + Prettier
npm run test:e2e -C frontend     # Playwright E2E tests
```

---

## Quality Enforcement Architecture

Four layers protect code quality. Ordered by independence from AI:

```
Layer 1: GITHUB ACTIONS CI (highest — fully independent, runs on GitHub servers)
  → Runs on every push/PR: backend tests, frontend build+lint, code quality checks
  → Checks: hardcoded colors, 'any' types, missing auth, hard deletes
  → Config: .github/workflows/ci.yml

Layer 2: GIT PRE-COMMIT HOOK (high — system-enforced locally)
  → Blocks commit if: hardcoded colors, 'any' types, missing auth, build fails, tests fail
  → Config: .githooks/pre-commit

Layer 3: CLAUDE CODE HOOKS (medium-high — runs after every file edit)
  → validate-frontend-v2.sh: 10 checks (ERRORS block, WARNINGS inform)
  → validate-backend.sh: auth deps, safe_commit, soft_delete, SQL injection
  → validate-wiring.sh: checks new components are imported somewhere

Layer 4: CLAUDE.MD RULES + CHECKLISTS (medium — self-enforced by AI)
  → Subject to drift. Layers 1-3 catch what I miss.
```

**"Agent teams" are NOT independent agents.** The real independence comes from
system-level enforcement (git hooks, CI), not from AI self-policing.

---

## Zero Trial-and-Error Policy

**NEVER guess. NEVER try and see. ALWAYS research first.**

1. **READ documentation first** — `man`, `--help`, official docs via WebSearch
2. **CHECK prerequisites** — versions, OS, architecture, permissions, ports
3. **VERIFY environment** — what's installed, what's running, what's configured
4. **THEN execute** — one correct command, not 4 failed attempts

```
Before ANY system command — STOP and answer:
1. What OS/version am I targeting?
2. What's already installed? (which, dpkg -l)
3. What are exact prerequisites? (read docs, don't guess)
4. What's the exact command for THIS environment?
5. What could go wrong? (ports, permissions, disk space)
```

**If something fails:** Read the error completely → understand root cause → fix it.
Don't try a different command — fix the actual problem.

---

## Context Drift Prevention

**Rules don't expire. Chat 1 = Chat 50. No gradual relaxation.**

**Signs of drift (self-check):**
- "I'll just quickly..." → STOP
- "This is a small change..." → STOP
- "Let me try..." → STOP. Research first.
- Hardcoding a color → STOP. Use the variable.
- Skipping `data-testid` → STOP. Add it.

**The 3-task self-audit** — every 3 tasks, verify:
- Am I still following the design system? (no hardcoded colors?)
- Am I still running tests before declaring done?
- Am I still using existing components instead of creating new?
- Am I still handling errors properly?

---

## Mandatory Workflow

Every task MUST follow this sequence. No shortcuts.

### 1. UNDERSTAND before touching code
- Read ALL files you plan to modify + related files
- **Frontend UI work:** Reference `frontend/tiling-preview-v3.html` for visual patterns
- For infra tasks: check OS, versions, prerequisites FIRST
- **Model/DB changes:** Run Model Change Protocol below BEFORE opening any model file

#### Model Change Protocol — MANDATORY before editing `app/models/*.py`

```bash
# 1. Find ALL usages of the changed fields/class across entire codebase
grep -rn "FieldName\|ClassName" app/ tests/ alembic/ scripts/ --include="*.py"

# 2. List existing migration revision IDs (avoid collision)
python3 -c "
import glob, re
for f in sorted(glob.glob('alembic/versions/*.py')):
    c = open(f).read()
    m = re.search(r\"revision(?:\s*:\s*str)?\s*=\s*['\\\"](.*?)['\\\"]\", c)
    if m: print(m.group(1), f.split('/')[-1])
"

# 3. Map ALL affected files BEFORE first edit:
#    models → schemas → routers → services → tests → seed_data → migrations
```

**Teprve po tomto researchi** udělej VŠECHNY změny najednou. Jeden průchod, ne iterace.
`model-impact.sh` hook tě po každé editaci modelu upozorní na zbývající reference.

### 2. PLAN before implementing
- For any change touching 3+ files → use EnterPlanMode
- For infra tasks: write exact commands and verify correctness for target environment

### 3. IMPLEMENT following existing patterns
- Copy patterns from existing code, don't invent new ones
- **ONE correct attempt, not multiple guesses**

### 4. TRACE THE WIRE — verify feature is actually connected

**Build passing ≠ feature working.**

```
User clicks button
  → @click handler in template?
    → handler calls store action or API? (not just console.log)
      → store action calls API module?
        → API module calls correct endpoint?
          → endpoint registered in router?
            → router calls service?
              → response flows back to component?
                → component renders result? (v-if/v-for)
                  → component imported in parent?
                    → component used in parent template?
```

**Wiring Checklist:**
- [ ] Component imported in parent (`import X from ...`)
- [ ] Component used in parent template (`<X />`)
- [ ] If `v-if` — condition is actually true in normal flow
- [ ] Props match what child expects
- [ ] Event handlers wired (`@click`, `@submit`, `@drop`, etc.)
- [ ] Handler calls actual API/store
- [ ] API response stored and rendered
- [ ] New route/endpoint registered in router/app

### 5. RUN CHECKS
- `python3 gestima.py test` — MUST pass
- `npm run build -C frontend` — MUST pass with zero errors
- `npm run lint -C frontend` — MUST pass
- E2E if UI behavior changed: `npm run test:e2e -C frontend`

### 6. REPORT results
- Show complete wire trace, changed files, test/build output summary

---

## Architecture

```
app/                          # Backend (FastAPI, Python)
├── config.py                 # Pydantic BaseSettings
├── gestima_app.py            # App setup, middleware, routes
├── database.py               # SQLAlchemy async, AuditMixin
├── dependencies.py           # Auth (get_current_user, require_role)
├── db_helpers.py             # set_audit, safe_commit, soft_delete
├── models/                   # SQLAlchemy models (25 tables)
├── routers/                  # FastAPI routers (30+)
├── schemas/                  # Pydantic v2 schemas
└── services/                 # Business logic (43 modules)

frontend/src/                 # Frontend (Vue 3, TypeScript)
├── api/                      # Axios API modules (20)
│   └── client.ts             # apiClient + adminClient
├── assets/css/
│   ├── design-system.css     # v6.0 — 51 v2 tokens
│   ├── tailwind.css
│   ├── base.css
│   └── modules/
├── components/
│   ├── ui/                   # Atomic: Button, DataTable, Dialog, Toast
│   └── modules/              # Feature modules
├── composables/              # useDialog, useDarkMode, useResizeHandle...
├── stores/                   # Pinia stores (12)
├── types/                    # TypeScript interfaces (23 files)
├── utils/                    # formatCurrency, formatDate, formatNumber
├── views/                    # Page-level components
└── router/index.ts           # Vue Router with auth guards

tests/                        # Backend tests (pytest)
frontend/e2e/                 # E2E tests (Playwright)
```

---

## Key Domain Concepts

- **Part (Díl)** — manufactured piece with operations, materials, batches
- **Operation (Operace)** — machining step on a work center (ordered by seq)
- **Feature (Prvek)** — geometric element within an operation (cavity, hole, etc.)
- **MaterialInput** — material stock assigned to a part (1:N, ADR-024)
- **Batch (Dávka)** — production quantity with pricing snapshot
- **BatchSet** — group of batches for pricing families (ADR-022)
- **WorkCenter (Pracoviště)** — machine/work center with hourly rates
- **Quote (Nabídka)** — customer quote (DRAFT→SENT→APPROVED/REJECTED)
- **Partner** — customer/supplier/both

## File Ownership

| Když měníš... | Zkontroluj/aktualizuj také... |
|---|---|
| `app/models/xyz.py` | `app/schemas/xyz.py`, `app/routers/xyz_router.py`, `tests/test_xyz.py` |
| `app/routers/xyz_router.py` | `app/services/xyz_service.py`, `tests/test_xyz.py` |
| `frontend/src/types/xyz.ts` | `frontend/src/api/xyz.ts`, komponenty používající tento typ |
| `frontend/src/api/xyz.ts` | `frontend/src/stores/xyz.ts`, `frontend/src/types/xyz.ts` |
| `frontend/src/stores/xyz.ts` | Komponenty používající tento store |
| `frontend/src/assets/css/design-system.css` | Všechny komponenty používající změněné tokeny |

---

## Security Checklist

- [ ] No secrets in code (use .env)
- [ ] Auth dependency on every endpoint
- [ ] No raw SQL / f-string queries
- [ ] No path traversal in file operations
- [ ] Input validation via Pydantic schemas
- [ ] Rate limiting on sensitive endpoints
- [ ] CORS configured correctly

---

## Documentation Policy — ADR Workflow

### Kdy psát ADR (a kdy NE)

| Piš ADR | NIC nepíš |
|---|---|
| Nový architektonický pattern s tradeoffs | Bugfix |
| Breaking change datového modelu | Nový endpoint podle vzoru |
| Integrace třetí strany | UI komponenta |
| Bezpečnostní model | Rozšíření existujícího ADR |
| Neobvyklé rozhodnutí které by budoucí Claude "opravil" | Test, refactor, cleanup |

**Pravidlo:** Ptej se — *"Pochopí Claude z kódu proč to tak je?"* Pokud ano → žádný ADR.

### ADR Workflow

```
1. PLÁNOVÁNÍ  → plný ADR (kontext + alternativy + tradeoffs)
2. IMPLEMENTACE → kód + testy
3. PO IMPLEMENTACI → vytvoř kompaktní ADR (max 35 řádků)
                   → přesuň plný ADR do docs/ADR/archive/
                   → .claudeignore ignoruje archive/ → žádný noise
```

### Kompaktní ADR šablona (max 35 řádků)

```markdown
# ADR-NNN: Název [ACCEPTED | PARTIAL | PLANNED | SUPERSEDED BY ADR-XXX]
> Archive: docs/ADR/archive/NNN-filename.md — Claude může požádat o přečtení

## Rozhodnutí
Jedna věta co bylo rozhodnuto.

## Pattern
- `app/models/xyz.py` — co zde najdeš
- `frontend/src/` — kde žije frontend část

## Nesmíš
- co nedělat (1-3 bullets)
```

### CHANGELOG

- Claude **neudržuje CHANGELOG** automaticky — jen na explicitní žádost
- Aktualizuj ručně při releasu (ne per-task)
- Formát: verze + datum + max 5 bulletů

### Existující ADRy

Kompaktní ADRy jsou v `docs/ADR/` (Claude je čte).
Plné originály jsou v `docs/ADR/archive/` (Claude je NEČTE — .claudeignore).
Pokud potřebuješ plný kontext → řekni Claudovi: *"Přečti docs/ADR/archive/NNN-..."*

---

## Subagent Model Policy

Ad-hoc `Task` subagenty spouštěj vždy s explicitním modelem:

| Účel | Model |
|------|-------|
| Coding, refactoring, dokumenty | `sonnet` |
| Jednoduchý research, search | `haiku` |
| Audit, architektura, komplexní debugging | `opus` |

**NIKDY nespoléhej na dědičnost od rodiče.** Vždy zadej `model` v `Task` tool callu.

---

## Git — omezení výstupu

```bash
git log --oneline -10           # přehled, NE bez -n limitu
git diff --stat HEAD            # summary, NE celý diff
git show --stat HEAD | tail -3  # jen summary
git show --stat <hash> | tail -1  # zjisti velikost před čtením staršího commitu
```

## Git Conventions

```
feat(scope): add new feature
fix(scope): fix bug description
refactor(scope): restructure without behavior change
test(scope): add or update tests
chore(scope): maintenance, cleanup
docs(scope): documentation updates
```

Scopes: `backend`, `frontend`, `db`, `auth`, `pricing`, `materials`, `infor`, `e2e`
