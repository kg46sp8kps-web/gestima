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

```
Layer 1: GITHUB ACTIONS CI — runs on every push/PR
Layer 2: GIT PRE-COMMIT HOOK — blocks commit locally
Layer 3: CLAUDE CODE HOOKS — validates after every file edit
Layer 4: CLAUDE.MD RULES — self-enforced by AI (least reliable)
```

---

## Workflow

1. **READ first** — přečti soubory které budeš měnit + related files
2. **Model/DB changes** → Model Change Protocol (viz níže)
3. **3+ files** → use EnterPlanMode
4. **After implementation** → run tests + build + lint
5. **Verify wiring** — Wire Tracing Checklist (viz níže)

### Model Change Protocol — MANDATORY before editing `app/models/*.py`

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

### Wire Tracing Checklist

```
User clicks button
  → @click handler in template?
    → handler calls store action or API?
      → store action calls API module?
        → API module calls correct endpoint?
          → endpoint registered in router?
            → router calls service?
              → response flows back to component?
                → component renders result?
                  → component imported in parent?
                    → component used in parent template?
```

---

## Architecture

```
app/                          # Backend (FastAPI, Python)
├── config.py                 # Pydantic BaseSettings
├── gestima_app.py            # App setup, middleware, routes
├── database.py               # SQLAlchemy async, AuditMixin
├── dependencies.py           # Auth (get_current_user, require_role)
├── db_helpers.py             # set_audit, safe_commit, soft_delete
├── models/                   # SQLAlchemy models (28 tables) + inline Pydantic schemas
├── routers/                  # FastAPI routers (32)
├── schemas/                  # Pydantic v2 schemas (6 standalone — většina inline v models/)
└── services/                 # Business logic (43 modules)

frontend/src/                 # Frontend (Vue 3, TypeScript)
├── api/                      # Axios API modules (25)
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
├── types/                    # TypeScript interfaces (24 files)
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
| `app/models/xyz.py` | inline schemas ve stejném souboru, `app/routers/xyz_router.py`, `tests/test_xyz.py` |
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

## ADR

Piš ADR jen pro architektonická rozhodnutí s tradeoffs. Kompaktní ADRy v `docs/ADR/`, plné v `docs/ADR/archive/`.

### Kompaktní ADR šablona (max 35 řádků)

```markdown
# ADR-NNN: Název [ACCEPTED | PARTIAL | PLANNED | SUPERSEDED BY ADR-XXX]
> Archive: docs/ADR/archive/NNN-filename.md

## Rozhodnutí
Jedna věta co bylo rozhodnuto.

## Pattern
- `app/models/xyz.py` — co zde najdeš
- `frontend/src/` — kde žije frontend část

## Nesmíš
- co nedělat (1-3 bullets)
```

## Subagent Model Policy

| Účel | Model |
|------|-------|
| Coding, refactoring | `sonnet` |
| Research, search | `haiku` |
| Audit, architektura, debugging | `opus` |

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
