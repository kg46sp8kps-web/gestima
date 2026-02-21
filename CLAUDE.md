# GESTIMA — AI Development Rules

> CNC cost calculator. FastAPI + Vue 3 + SQLite. Version 2.0.0.
> Czech UI labels, English code. Production app — no experiments.

## Quick Commands

```bash
python3 gestima.py dev          # Backend :8000 + Frontend :5173
python3 gestima.py test         # All pytest tests
python3 gestima.py test-critical # Critical tests only
npm run build -C frontend       # Type-check + production build
npm run lint -C frontend        # ESLint + Oxlint + Prettier
npm run test:e2e -C frontend    # Playwright E2E tests
```

## Quality Enforcement Architecture

Four layers protect code quality. Ordered by independence from AI:

```
Layer 1: GITHUB ACTIONS CI (highest — fully independent, runs on GitHub servers)
  → Runs on every push/PR: backend tests, frontend build+lint, code quality checks
  → Checks: hardcoded colors, 'any' types, missing auth, hard deletes
  → I (Claude) have ZERO control over this. It passes or it doesn't.
  → Config: .github/workflows/ci.yml

Layer 2: GIT PRE-COMMIT HOOK (high — system-enforced locally)
  → Blocks commit if: hardcoded colors, 'any' types, missing auth, build fails, tests fail
  → Runs automatically before every git commit.
  → Config: .githooks/pre-commit (activated via git config core.hooksPath)

Layer 3: CLAUDE CODE HOOKS (medium-high — runs after every file edit)
  → validate-frontend.sh: 12 checks — colors, inline styles, any, !important, axios,
    @media queries, scoped styles, hardcoded font-size, rgb/rgba/hsl, Options API, lucide imports
  → validate-backend.sh: checks auth deps, safe_commit, soft_delete, SQL injection
  → validate-wiring.sh: checks new components are imported somewhere
  → Catches issues in real-time during editing.

Layer 4: CLAUDE.MD RULES + CHECKLISTS (medium — self-enforced by AI)
  → Design system, naming, patterns, workflow
  → Subject to drift in long conversations. Layers 1-3 catch what I miss.
```

**Reality check:** Layers 1-2 are completely independent of AI behavior.
Layer 3 runs automatically but AI could theoretically work around it.
Layer 4 depends on AI discipline — the weakest link, but backed by 3 stronger layers.

**"Agent teams" are NOT independent agents.** All sub-agents are the same AI with
different instructions. The real independence comes from system-level enforcement
(git hooks, CI pipeline), not from AI self-policing.

---

## Zero Trial-and-Error Policy

**NEVER guess. NEVER try and see. ALWAYS research first.**

This is the #1 rule. When you don't know something:

1. **READ documentation first** — `man`, `--help`, official docs via WebSearch
2. **CHECK prerequisites** — versions, OS, architecture, permissions, disk space, ports
3. **VERIFY environment** — what's installed, what's running, what's configured
4. **THEN execute** — one correct command, not 4 failed attempts

### Before ANY system/infrastructure command:
```
STOP. Answer these questions first:
1. What OS/distro/version am I targeting?
2. What's already installed? (check with `which`, `dpkg -l`, `rpm -qa`, etc.)
3. What are the exact prerequisites? (read official docs, not guess)
4. What's the exact command for THIS specific environment?
5. What could go wrong? (check ports, permissions, disk space)
```

### Examples of what NOT to do:
```
❌ "Let me try apt install X..."       → fails → "Let me try apt-get..." → fails → "Maybe yum?"
❌ "Let me try port 80..."             → fails → "Let me try 8080..." → fails → "Maybe 3000?"
❌ "Let me add this config..."         → fails → "Let me try different syntax..." → fails

✅ First: "uname -a && cat /etc/os-release" → know the OS
✅ First: "ss -tlnp | grep :80" → know what's using the port
✅ First: Read the official docs for this specific version
✅ THEN: Execute the correct command once
```

### If something fails:
1. **READ the error message completely** — don't skip it
2. **UNDERSTAND the root cause** — don't just try a different command
3. **FIX the actual problem** — don't work around it
4. **If you don't understand the error** — tell the user honestly, don't keep trying random fixes

---

## Context Drift Prevention

**Rules don't expire. Chat 1 = Chat 50. No gradual relaxation.**

### At the START of every task (even mid-conversation):
1. Mentally re-read the rules that apply to this task
2. If working on frontend → design system tokens, reusable components, TypeScript strict
3. If working on backend → AuditMixin, auth dependency, safe_commit, soft_delete
4. If working on infra/deployment → Zero Trial-and-Error Policy above

### Signs of drift (self-check):
- "I'll just quickly..." → STOP. Quick doesn't mean skip rules
- "This is a small change..." → STOP. Small changes follow the same rules
- "Let me try..." → STOP. Research first, execute second
- Hardcoding a color because "it's just one place" → STOP. Use the variable
- Skipping `data-testid` because "it's not important" → STOP. Add it
- Skipping tests because "the change is trivial" → STOP. Run them

### The 3-task self-audit:
Every 3 completed tasks within a conversation, pause and verify:
- Am I still following the design system? (no hardcoded colors?)
- Am I still running tests before declaring done?
- Am I still using existing components instead of creating new ones?
- Am I still handling errors properly?
- Am I still adding data-testid to interactive elements?

**If you catch yourself drifting, acknowledge it and correct immediately.**

---

## Mandatory Workflow

Every task MUST follow this sequence. No exceptions. No shortcuts.

### 1. UNDERSTAND before touching code
- Read ALL files you plan to modify
- Read related files (if editing a router, read the corresponding service, model, schema)
- **For frontend UI work:** Reference `frontend/template.html` for visual patterns (open in browser or read the CSS/HTML sections for the component type you're building)
- Understand the existing pattern before proposing changes
- For infra/deployment tasks: check OS, versions, prerequisites FIRST

### 2. PLAN before implementing
- For any change touching 3+ files, use EnterPlanMode
- Identify all files that need changes
- Verify the plan follows rules below
- For infra tasks: write the exact commands you'll run and verify each one is correct for the target environment

### 3. IMPLEMENT following existing patterns
- Copy patterns from existing code, don't invent new ones
- If unsure, search the codebase for how it's done elsewhere
- If unsure about a system command, read the docs first (WebSearch, `man`, `--help`)
- **ONE correct attempt, not multiple guesses**

### 4. TRACE THE WIRE — verify feature is actually connected

**This is the most important step. Build passing ≠ feature working.**

After implementing, trace the COMPLETE path from user action to visible result:

```
User clicks button
  → component has @click handler? (check template)
    → handler calls store action or API? (check <script>)
      → store action calls API module? (check store)
        → API module calls correct endpoint? (check api/)
          → endpoint exists in router? (check router)
            → router calls service? (check service)
              → service returns correct data? (check logic)
            → response flows back to component? (check response handling)
          → component renders the result? (check template v-if/v-for)
        → is the component imported in parent? (check parent imports)
      → is the component actually rendered? (check parent template)
    → is there a v-if that hides it? (check conditions)
```

**Wiring Checklist (verify EVERY link in the chain):**

- [ ] New component is imported in its parent (`import X from ...`)
- [ ] New component is used in parent template (`<X />` or `<X v-if="..." />`)
- [ ] If conditional (`v-if`), the condition is actually true in normal flow
- [ ] Props passed from parent match what child expects
- [ ] Event handlers are wired (`@click`, `@submit`, `@dragstart`, `@drop`, etc.)
- [ ] Handler calls the actual API/store (not just console.log or empty function)
- [ ] API response is stored and rendered (not fetched and discarded)
- [ ] If new route/endpoint — it's registered in router/app

**How to verify without a browser:**
```bash
# Check if component is imported anywhere
grep -r "ComponentName" frontend/src/ --include='*.vue' --include='*.ts'

# Check if API endpoint is called from frontend
grep -r "/api/new-endpoint" frontend/src/ --include='*.ts'

# Check if store action is used in any component
grep -r "store.newAction\|newAction(" frontend/src/ --include='*.vue'

# Check if new router is included in app
grep -r "new_router" app/gestima_app.py app/routers/__init__.py
```

**If ANY link is missing, the feature doesn't exist. Fix it before moving on.**

### 5. RUN CHECKS
- Run: `python3 gestima.py test` (backend)
- Run: `npm run build -C frontend` (type-check + build — MUST pass with zero errors)
- Run: `npm run lint -C frontend` (lint — MUST pass)
- If you changed E2E-testable behavior: `npm run test:e2e -C frontend`

### 6. REPORT results
- Show the **complete wire trace** — from user action to visible result
- Show which files were changed and how they connect
- Show test/build output summary

**If any check fails, fix it before proceeding. Never skip verification.**

---

## Reusable Components — USE BEFORE CREATING NEW

**Before creating ANY new component, check this list. Duplicating existing functionality is a CRITICAL violation.**

### UI Components (`components/ui/`)

| Component | Purpose | Key Props |
|---|---|---|
| **Button.vue** | Multi-variant button | `variant` (primary/secondary/danger/ghost), `size`, `loading`, `disabled` |
| **Input.vue** | Text/number/password input with validation | `modelValue`, `label`, `type`, `error`, `hint`, `mono` |
| **Select.vue** | Native select dropdown | `modelValue`, `options` ({value,label}[]), `placeholder`, `error` |
| **Modal.vue** | Dialog modal (Teleport) | `modelValue`, `title`, `size` (sm/md/lg/xl), slots: header/default/footer |
| **FormTabs.vue** | Tab layout for forms | `tabs` (string[]), `modelValue` (active index), `vertical`, `keepAlive` |
| **DataTable.vue** | Full data grid (sort/select/paginate) | `data`, `columns` (Column[]), `loading`, `selectable`, `pagination` |
| **ColumnChooser.vue** | Column visibility toggle | `columns`, `storageKey` (localStorage persistence) |
| **AlertDialog.vue** | Alert modal (via useDialog) | Driven by `useDialog().alert()` — promise-based |
| **ConfirmDialog.vue** | Confirm modal (via useDialog) | Driven by `useDialog().confirm()` — returns boolean |
| **ToastContainer.vue** | Toast notifications | Driven by `useUiStore().showSuccess/Error/Warning()` |
| **Tooltip.vue** | Cursor-following tooltip | `text`, `delay` |
| **DragDropZone.vue** | File upload drag & drop | `accept`, `maxSize`, `label`, emits `upload` |
| **Spinner.vue** | Loading spinner | `size`, `text`, `inline` |
| **CuttingModeButtons.vue** | LOW/MID/HIGH toggle | `mode`, `disabled`, emits `change` |
| **CoopSettings.vue** | Subcontractor settings panel | `isCoop`, `coopPrice`, `coopDays`, `disabled` |
| **TypeAheadSelect.vue** | Autocomplete with keyboard | `options`, `modelValue`, `placeholder`, `maxVisible` |

### Composables (`composables/`)

| Composable | Purpose | Returns |
|---|---|---|
| **useDialog()** | Confirm/alert dialogs (promise-based) | `confirm(options)`, `alert(options)` |
| **useDarkMode()** | Theme toggle | `isDark`, `toggle()`, `setTheme()` |
| **useResizeHandle()** | Panel resize drag | `size`, `isDragging`, `startResize()`, `resetSize()` |
| **useResizablePanel()** | Split-pane resize | `panelWidth`, `isDragging`, `startResize()` |
| **useKeyboardShortcuts()** | Keyboard shortcut system | `registerShortcut()`, `unregisterAll()` |
| **usePartLayoutSettings()** | Horizontal/vertical layout | `layoutMode`, `toggleLayout()` |
| **useLinkedWindowOpener()** | Cross-module window linking | `openLinked(module, title)` |
| **usePrefetch()** | Background data preload | `prefetchAll()` |

### Utilities (`utils/`)

| Function | Purpose | Example |
|---|---|---|
| `formatCurrency(value)` | Czech currency format | `1 234,50 CZK` |
| `formatNumber(value)` | Czech number format | `1 234,5` |
| `formatDate(value)` | Czech date format | `21. 2. 2026` |
| `formatPrice(value)` | Price with 2 decimals | `1 234,50` |
| `partStatusLabel(status)` | Status → Czech label | `active` → `Aktivní` |
| `partSourceLabel(source)` | Source → Czech label | `manual` → `Manuální` |

### Directives

| Directive | Purpose | Usage |
|---|---|---|
| `v-select-on-focus` | Select all text on input focus | `<input v-select-on-focus />` |

---

## Performance Rules

### Budgets — HARD LIMITS

| Metric | Limit | How to verify |
|---|---|---|
| API response (list endpoints) | < 200ms | Check FastAPI logs |
| API response (detail/CRUD) | < 100ms | Check FastAPI logs |
| Frontend initial load (LCP) | < 2s | Lighthouse |
| Vue component render | < 16ms (60fps) | Vue DevTools |
| Bundle chunk size | < 600KB per chunk | `npm run build` warning |
| Component LOC | < 500 LOC (split if larger) | `wc -l` |

### Backend Performance — MANDATORY

1. **Eager loading for list endpoints** — always use `selectinload()` or `joinedload()`:
   ```python
   # CORRECT — prevents N+1 queries
   query = select(Part).options(
       selectinload(Part.operations),
       selectinload(Part.material_inputs).joinedload(MaterialInput.price_category)
   ).where(Part.deleted_at.is_(None))

   # WRONG — causes N+1 queries
   query = select(Part).where(Part.deleted_at.is_(None))
   # then accessing part.operations triggers lazy load per part
   ```
2. **Pagination on ALL list endpoints** — `skip` + `limit` with max 500
3. **No blocking operations** — everything async (`await`), no `time.sleep()`
4. **Index frequently queried columns** — `deleted_at`, foreign keys, `created_at`

### Frontend Performance — MANDATORY

1. **Lazy-load routes** — all routes use `() => import('@/views/...')`
2. **Lazy-load heavy modules** — use `defineAsyncComponent()` for modules in WindowsView
3. **Lazy-load heavy libraries** — PDF.js, Three.js etc. via dynamic `import()`:
   ```typescript
   // CORRECT — loaded only when needed
   const pdfjsLib = await import('pdfjs-dist')

   // WRONG — loaded on app init
   import * as pdfjsLib from 'pdfjs-dist'
   ```
4. **Virtualize long lists** — use `@tanstack/vue-virtual` for lists > 50 items:
   ```typescript
   import { useVirtualizer } from '@tanstack/vue-virtual'
   ```
5. **Debounce user input** — search, filters, resize: min 300ms debounce
   ```typescript
   let timer: ReturnType<typeof setTimeout>
   function onSearch(query: string) {
     clearTimeout(timer)
     timer = setTimeout(() => store.fetchFiltered(query), 300)
   }
   ```
6. **No expensive computed without memoization** — if filtering large arrays (>100 items), cache results
7. **v-for always with :key** — unique key on every list render
8. **Clean up watchers and listeners** — use `onUnmounted()` or let `<script setup>` handle it
9. **No deep watchers on large objects** — use specific property watchers instead

### NEVER do this (Performance)

- ❌ Fetch all records without pagination
- ❌ Import heavy libraries at top level (use dynamic import)
- ❌ Use `watch(..., { deep: true })` on large objects/arrays
- ❌ Create computed properties that filter the same array multiple times (use single pass)
- ❌ Re-render entire lists without virtualization (>50 items)
- ❌ Add new npm dependencies > 100KB without justification

---

## Data & Architecture Principles

**Tyto principy zajišťují konzistenci a bezpečnost dat. Porušení = kaskádové problémy.**

### 1. Single Source of Truth — výpočty POUZE na backendu

```
Backend (PRAVDA)                    Frontend (ZOBRAZENÍ)
├── price_calculator.py             ├── Zobrazí batch.unit_cost
├── material_calculator.py          ├── Zobrazí batch.material_percent
├── feature_calculator.py           ├── Zobrazí formátovanou cenu
├── batch_service.py                └── NIKDY nepočítá ceny/náklady
└── accounting_router.py
```

**Pravidla:**
- **Ceny, náklady, marže, procenta** → počítá POUZE backend (services/)
- **Frontend POUZE zobrazuje** hodnoty z API response
- **Formátování ≠ výpočet** — `formatCurrency(value)` na frontendu je OK, `price * quantity * margin` NENÍ
- **Pokud potřebuješ novou odvozenou hodnotu** → přidej ji jako `@computed_field` v Pydantic modelu nebo jako pole v response schema, ne jako computed v .vue komponentě
- **Duplicitní vzorec = bug** — pokud stejný výpočet existuje v backendu i frontendu, smaž frontend verzi

### 2. Jednosměrný data flow

```
API response → Pinia store → Component → Template
     ↑                                       |
     └──── User action → Store action → API call
```

**Pravidla:**
- **Komponenty NEVOLAJÍ API přímo** — vždy přes store action nebo api/ modul
- **Komponenty NEMUTUJÍ store přímo** — vždy přes store actions
- **Stores si NESLEDUJÍ navzájem** — žádný `watch(otherStore.value)` across stores
- **Props down, events up** — parent → child přes props, child → parent přes emit

### 3. Datová integrita

- **Optimistic locking na KAŽDÉM update** — `version: int` v update schema, kontrola před save
- **Soft delete VŽDY** — `soft_delete()`, nikdy `db.delete()`
- **Audit trail VŽDY** — `AuditMixin` na každém modelu, `set_audit()` na každém write
- **Referenční integrita** — foreign keys v modelech, kaskádové soft-delete kde relevantní
- **Validace na hranici** — Pydantic schemas validují na vstupu do API, interní kód věří validated datům
- **Atomic operations** — `safe_commit()` zajistí rollback při chybě, žádné partial writes

### 4. Snapshot princip (ceny a historická data)

- **Batch ukládá ceny v momentě výpočtu** — ne reference na aktuální sazby
- **Quote ukládá snapshot cen** — změna sazby nezmění existující nabídku
- **Když se změní vstupní data** (sazba, materiál) → uživatel musí explicitně přepočítat
- **NIKDY automatický přepočet historických dat** — to by zfalšovalo historii

### 5. Konzistentní datové tvary

- **TypeScript typy MUSÍ odpovídat backend schemas** — `frontend/src/types/` = zrcadlo `app/schemas/`
- **Jméno typu = jméno schema** — `PartResponse` v backendu = `Part` interface ve frontendu
- **Update typy VŽDY mají `version: number`** — bez výjimky
- **Nullable pole** — pokud backend posílá `null`, frontend typ musí mít `| null`
- **Přidáš pole v backendu** → přidej ho i do frontend typu a API modulu

### 6. Fail-safe chování

- **Chybějící data = prázdný stav, ne crash** — `items.value ?? []`, ne `items.value!`
- **API chyba = toast + zachování stavu** — ne bílá obrazovka
- **4 stavy každého modulu:** loading, empty, error, data — vždy řešit všechny
- **Timeout na API calls** — apiClient má default timeout, neblokovat UI navěky

---

## Architecture

```
app/                          # Backend (FastAPI, Python)
├── config.py                 # Pydantic BaseSettings
├── gestima_app.py            # App setup, middleware, routes
├── database.py               # SQLAlchemy async, AuditMixin
├── dependencies.py           # Auth dependencies (get_current_user, require_role)
├── db_helpers.py             # set_audit, safe_commit, soft_delete
├── models/                   # SQLAlchemy models (25 tables)
├── routers/                  # FastAPI routers (30+)
├── schemas/                  # Pydantic v2 request/response schemas
└── services/                 # Business logic (43 modules)

frontend/src/                 # Frontend (Vue 3, TypeScript)
├── api/                      # Axios API clients (20 modules)
│   └── client.ts             # apiClient + adminClient setup
├── assets/css/
│   ├── design-system.css     # v4.0 — ALL design tokens (DO NOT duplicate)
│   ├── tailwind.css          # Utilities only
│   ├── base.css              # Body, layout
│   └── modules/              # Module-specific styles
├── components/
│   ├── ui/                   # Atomic: Button, DataTable, Dialog, Toast
│   └── modules/              # Feature modules (parts, operations, pricing...)
├── composables/              # Vue composables (useDialog, useDarkMode...)
├── stores/                   # Pinia stores (12 stores)
├── types/                    # TypeScript interfaces (23 files)
├── utils/                    # formatCurrency, formatDate, formatNumber
├── views/                    # Page-level components
└── router/index.ts           # Vue Router with auth guards

tests/                        # Backend tests (pytest)
frontend/e2e/                 # E2E tests (Playwright)
```

---

## Backend Rules

### Models — ALWAYS

1. **Every model uses AuditMixin** — provides created_at, updated_at, created_by, updated_by, deleted_at, deleted_by, version
2. **Never hard-delete** — use `soft_delete(db, instance, username)` from db_helpers
3. **Always set audit fields** — use `set_audit(instance, username)` for create, `set_audit(instance, username, is_update=True)` for update
4. **Optimistic locking** — every update schema MUST include `version: int` field. Check version before saving.
5. **Number generation** — use `NumberGenerator` with correct prefix range:
   - Parts: 10XXXXXX, Materials: 20XXXXXX, Batches: 30XXXXXX
   - BatchSets: 35XXXXXX, Quotes: 50XXXXXX, Partners: 70XXXXXX
   - WorkCenters: 80XXXXXX (sequential, not random)

### Routers — ALWAYS

1. **Auth dependency on every endpoint:**
   - Read endpoints: `current_user: User = Depends(get_current_user)`
   - Write endpoints: `current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.OPERATOR]))`
   - Admin endpoints: `current_user: User = Depends(require_role([UserRole.ADMIN]))`
2. **Use safe_commit()** for all database writes — never raw `db.commit()`
3. **Error pattern:**
   ```python
   except ValueError as e:
       raise HTTPException(status_code=400, detail=str(e))
   except HTTPException:
       raise
   except Exception as e:
       logger.error(f"Error: {e}", exc_info=True)
       raise HTTPException(status_code=500, detail="Interní chyba serveru")
   ```
4. **Pagination pattern:**
   ```python
   skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=500)
   ```
5. **Never use f-strings in SQL queries** — always use SQLAlchemy parameterized queries

### Schemas — ALWAYS

1. **Naming:** `XyzCreate`, `XyzUpdate`, `XyzResponse`
2. **XyzUpdate MUST have:** `version: int` (for optimistic locking)
3. **XyzResponse MUST have:** `model_config = ConfigDict(from_attributes=True)`
4. **Use Field() constraints** — min_length, max_length, ge, le, pattern

### Services — ALWAYS

1. **Inherit from BaseCrudService** when possible (see base_service.py)
2. **Business logic belongs in services**, not in routers
3. **Routers only handle:** HTTP concerns (request parsing, response formatting, status codes)

### NEVER do this (Backend)

- ❌ Hard-delete records (always soft-delete)
- ❌ Skip version check on updates
- ❌ Skip auth dependency on any endpoint
- ❌ Use raw SQL or f-strings in queries
- ❌ Return 200 for creation (use 200, our convention — NOT 201)
- ❌ Add new dependencies without checking requirements.txt first
- ❌ Create new model without AuditMixin
- ❌ Catch generic Exception and silently swallow it
- ❌ Skip logging on errors

---

## Frontend Rules

### Components — ALWAYS

1. **Use `<script setup lang="ts">`** — no Options API, no class components
2. **Scoped styles:** `<style scoped>` always
3. **Design tokens only** — never hardcode colors, use CSS variables:
   ```css
   /* CORRECT */
   color: var(--text-primary);
   background: var(--bg-surface);
   border: 1px solid var(--border-default);

   /* WRONG — NEVER DO THIS */
   color: #ffffff;
   background: #1a1a1a;
   border: 1px solid #333;
   ```
4. **Interactive elements MUST have `data-testid`** — buttons, inputs, links, rows
5. **Icons:** Lucide Vue Next, size via `ICON_SIZE` constant (18px) from `config/design.ts`
6. **Czech labels** — all user-visible text in Czech (no i18n library)
7. **Component size limits:**
   - Atomic (<200 LOC), Molecular (<500 LOC), Organism (<1000 LOC)
   - If larger, split into sub-components

### Design System (design-system.css) — MANDATORY REFERENCE

```css
/* Colors — ALWAYS use these variables, never raw hex */
--brand: #991b1b;           /* Primary red */
--bg-base: #0a0a0a;         /* App background */
--bg-surface: #141414;      /* Card/panel background */
--bg-raised: #1a1a1a;       /* Elevated surfaces */
--bg-input: #0f0f0f;        /* Input fields */
--text-primary: #ffffff;    /* Main text */
--text-body: #e5e5e5;       /* Body text */
--text-secondary: #a3a3a3;  /* Secondary text */
--text-muted: #737373;      /* Muted/disabled text */
--border-default: #262626;  /* Default borders */
--border-subtle: #1a1a1a;   /* Subtle borders */
--palette-success: #22c55e;
--palette-danger: #ef4444;
--palette-warning: #eab308;

/* Interactive states */
--hover: rgba(255,255,255,0.04);
--active: rgba(255,255,255,0.08);
--selected: rgba(255,255,255,0.06);
--focus-ring: rgba(255,255,255,0.5);

/* Spacing — rem-based */
--space-1: 0.25rem; --space-2: 0.5rem; --space-3: 0.75rem;
--space-4: 1rem; --space-6: 1.5rem; --space-8: 2rem;

/* Typography */
--text-xs: 0.6875rem; --text-sm: 0.75rem; --text-base: 0.8125rem;

/* Density system */
--density-row-height: 32px; /* compact */ or 40px /* comfortable */
```

**If you need a color, spacing, or size not defined here — ASK, don't invent.**

### Pinia Stores — ALWAYS

1. **Pattern:** Composition API with explicit return
   ```typescript
   export const useXyzStore = defineStore('xyz', () => {
     const items = ref<Xyz[]>([])
     const loading = ref(false)
     // ... actions and computeds
     return { items, loading, fetchItems, ... }
   })
   ```
2. **Loading state:** Use `useUiStore().startLoading()` / `stopLoading()` counter pattern
3. **Error handling:** `try/catch` with `useUiStore().showError(message)`
4. **Never** mutate store state from components — always use store actions

### API Calls — ALWAYS

1. **Use existing api/ modules** — never call axios directly from components
2. **Use `apiClient`** (regular) or **`adminClient`** (admin) from `api/client.ts`
3. **Handle errors with typed catches:**
   ```typescript
   try {
     const result = await partsApi.createPart(data)
     ui.showSuccess('Díl vytvořen')
   } catch (error) {
     if (error instanceof OptimisticLockErrorClass) {
       ui.showError('Data byla změněna jiným uživatelem. Obnovte stránku.')
     } else {
       ui.showError('Chyba při vytváření dílu')
     }
   }
   ```

### CSS/Styling — ALWAYS

1. **Use Tailwind utilities** for layout (flex, grid, gap, padding, margin)
2. **Use CSS variables** from design-system.css for colors, borders, backgrounds
3. **Never create new CSS files** — extend existing ones if needed
4. **Never add inline `style=""` attributes** — use classes or CSS variables
5. **Button variants:** `.btn-primary`, `.btn-secondary`, `.btn-destructive` (all ghost/transparent)
6. **Focus:** Always visible — `:focus-visible { outline: 2px solid var(--focus-ring) }` (WHITE, never blue)
7. **`<style scoped>` always** — never unscoped styles in .vue files
8. **`@container` queries** — never `@media` queries in components (container-aware layout)
9. **Font sizes via tokens** — `var(--text-xs)` minimum (13px). Never hardcode `font-size: Npx`

### UI/UX Patterns — APPROVED (follow exactly)

**Visual reference:** `frontend/template.html` — open in browser to see every pattern live.

| Pattern | Rule |
|---------|------|
| **Buttons** | Ghost only. 3 variants: `.btn-primary`, `.btn-secondary`, `.btn-destructive`. NO filled buttons. |
| **Icon buttons** | `.icon-btn` default grey → hover white. `.icon-btn-brand` for add/edit, `.icon-btn-danger` for delete. |
| **Badges** | Monochrome background + colored dot for status. `.badge` + `.badge-dot-ok/error/warn/neutral/brand`. |
| **Focus ring** | WHITE (`--focus-ring`). Never blue, never red, never brand color. |
| **Selected rows** | Neutral white overlay (`--selected`). Never brand-tinted. |
| **Edit mode** | `--bg-raised` + `--border-strong`. NOT red border. |
| **Toasts** | Monochrome body + colored left border (`.toast-ok/error/warn`). |
| **Status colors** | ONLY in: badge dots, toast left borders, chart segments. Never as button/badge background. |
| **Numbers & prices** | `font-family: var(--font-mono)` + `.col-num` (right-align) or `.col-currency` (right-align, nowrap). |
| **Layout** | `@container` queries, NOT `@media`. Fluid heights, NOT fixed px heights. |

### NEVER do this (Frontend) — hook-enforced where marked

- ❌ Hardcode colors (hex, rgb, rgba, hsl) — use CSS variables [HOOK-ENFORCED]
- ❌ Hardcode `font-size: Npx` — use `var(--text-*)` tokens [HOOK-ENFORCED]
- ❌ Use `any` type in TypeScript [HOOK-ENFORCED]
- ❌ Use `!important` in CSS [HOOK-ENFORCED]
- ❌ Add inline `style=""` attributes [HOOK-ENFORCED]
- ❌ Import axios directly in components [HOOK-ENFORCED]
- ❌ Use `@media` queries in components [HOOK-ENFORCED]
- ❌ Use `<style>` without `scoped` [HOOK-ENFORCED]
- ❌ Use Options API (`export default {}`) [HOOK-ENFORCED]
- ❌ Skip `data-testid` on interactive elements
- ❌ Skip error handling on API calls
- ❌ Ignore existing component patterns — copy them
- ❌ Add new npm packages without asking first
- ❌ Create new color/spacing values outside design-system.css
- ❌ Use filled/colored buttons (ghost only)
- ❌ Use colored badge backgrounds (monochrome + dot only)
- ❌ Use blue/red focus rings (white only)
- ❌ Use red border on edit mode (use `--border-strong`)
- ❌ Use emoji in UI (use Lucide icons)

---

## Database Rules

1. **Migrations via Alembic** — `alembic revision --autogenerate -m "description"`
2. **SQLite + WAL mode** — async via aiosqlite
3. **Every query filters soft-deleted:** `WHERE deleted_at IS NULL`
4. **Relationships use lazy loading** — use `selectinload()` or `joinedload()` explicitly when needed
5. **Never drop tables** — only add columns or create new tables

---

## Testing Rules

### When to write tests

- **New API endpoint** → write router test (test status codes, auth, validation)
- **New business logic** → write service test (test calculations, edge cases)
- **Bug fix** → write regression test that reproduces the bug first
- **New UI workflow** → update E2E test if existing spec covers it

### Backend test pattern

```python
@pytest.mark.asyncio
async def test_create_xyz(client: AsyncClient, admin_headers):
    response = await client.post("/api/xyz", json={...}, headers=admin_headers)
    assert response.status_code == 200
    result = response.json()
    assert result["field"] == expected_value
```

### E2E test pattern

```typescript
test('should create part', async ({ page }) => {
  await login(page)
  await setupWindowsView(page)
  await openModuleViaMenu(page, 'Part Main')
  await waitForModuleLoad(page)
  // ... assertions with data-testid selectors
})
```

### Test verification checklist

- [ ] All existing tests pass (`python3 gestima.py test`)
- [ ] Frontend builds without errors (`npm run build -C frontend`)
- [ ] Linting passes (`npm run lint -C frontend`)
- [ ] New code has test coverage for critical paths

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

When editing code, always check if related files need updates:

| If you change... | Also check/update... |
|---|---|
| `app/models/xyz.py` | `app/schemas/xyz.py`, `app/routers/xyz_router.py`, `tests/test_xyz.py` |
| `app/routers/xyz_router.py` | `app/services/xyz_service.py`, `tests/test_xyz.py` |
| `frontend/src/types/xyz.ts` | `frontend/src/api/xyz.ts`, components using this type |
| `frontend/src/api/xyz.ts` | `frontend/src/stores/xyz.ts`, `frontend/src/types/xyz.ts` |
| `frontend/src/stores/xyz.ts` | Components using this store |
| `frontend/src/assets/css/design-system.css` | All components using changed tokens |

---

## Code Quality Standards

### Import Order (Python)
```python
# 1. Standard library
import logging
from datetime import datetime
from typing import List, Optional

# 2. Third-party
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# 3. Local app
from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.models.user import User, UserRole
from app.db_helpers import set_audit, safe_commit, soft_delete
```

### Import Order (TypeScript/Vue)
```typescript
// 1. Vue core
import { ref, computed, watch, onMounted } from 'vue'

// 2. Third-party libraries
import { useRouter } from 'vue-router'
import { SomeIcon } from 'lucide-vue-next'

// 3. Local stores, composables
import { useUiStore } from '@/stores/ui'
import { useDialog } from '@/composables/useDialog'

// 4. Local API, types, utils
import * as partsApi from '@/api/parts'
import type { Part, PartCreate } from '@/types/part'
import { formatCurrency } from '@/utils/formatters'

// 5. Local components
import Button from '@/components/ui/Button.vue'

// 6. Constants
import { ICON_SIZE } from '@/config/design'
```

### Naming Conventions

| Context | Convention | Example |
|---|---|---|
| Python files | snake_case | `material_parser.py` |
| Python classes | PascalCase | `MaterialInput` |
| Python functions | snake_case | `get_price_per_kg` |
| Vue components | PascalCase | `PartDetailPanel.vue` |
| Vue composables | camelCase with `use` | `useDialog.ts` |
| TS types/interfaces | PascalCase | `PartCreate`, `MaterialResponse` |
| TS functions | camelCase | `fetchParts()` |
| CSS classes | kebab-case | `.btn-primary`, `.panel-header` |
| CSS variables | kebab-case with prefix | `--bg-surface`, `--text-primary` |
| API routes | kebab-case plural | `/api/material-inputs` |
| DB tables | snake_case plural | `material_inputs` |
| data-testid | kebab-case | `create-part-button` |

### Error Handling — Complete Pattern

**Backend:**
```python
# Service layer — raise ValueError for business errors
def validate_quantity(qty: int):
    if qty <= 0:
        raise ValueError("Množství musí být kladné číslo")

# Router layer — catch and convert to HTTP
@router.post("/")
async def create(data: CreateSchema, db=Depends(get_db), user=Depends(get_current_user)):
    try:
        result = await service.create(db, data, user.username)
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chyba: {e}", exc_info=True)
        raise HTTPException(500, "Interní chyba serveru")
```

**Frontend:**
```typescript
// Store/composable — catch and show feedback
async function savePart(data: PartCreate) {
  ui.startLoading()
  try {
    const result = await partsApi.create(data)
    ui.showSuccess('Díl uložen')
    return result
  } catch (error) {
    if (error instanceof OptimisticLockErrorClass) {
      ui.showError('Data byla změněna jiným uživatelem. Obnovte stránku.')
    } else if (error instanceof ValidationErrorClass) {
      ui.showError('Neplatná data: ' + error.message)
    } else {
      ui.showError('Chyba při ukládání dílu')
    }
    throw error  // Re-throw so caller knows it failed
  } finally {
    ui.stopLoading()  // ALWAYS stop loading, even on error
  }
}
```

### Dead Code Prevention

- Delete unused imports immediately
- Delete unused variables, functions, components
- Never comment-out code "for later" — use git history
- Never add `_unused` prefix to keep dead code
- If a feature is removed, remove ALL related code (model, router, service, schema, test, component, store, API module, types)

### Dependency Management

- **Python:** Check `requirements.txt` before adding. Pin versions.
- **Frontend:** Check `package.json` before adding. Ask user before `npm install`.
- **Size budget:** No new dependency > 100KB uncompressed without explicit approval
- **Prefer built-in** over adding a library (e.g., use native `fetch` events, Vue's `watch`, CSS transitions)

### Accessibility Basics

- All interactive elements focusable (buttons, inputs, links)
- `:focus-visible` outline on keyboard navigation
- Form inputs have labels (visible or `aria-label`)
- Color is not the only indicator (add text/icon for status)
- Toast notifications are dismissible
