# GESTIMA - Multi-Agent System Architecture

**Version:** 1.0
**Date:** 2026-01-31
**Status:** 🚀 Active

---

## 📋 OVERVIEW

GESTIMA používá **7-agent orchestration system** pro paralelní vývoj full-stack ERP aplikace.

**Klíčové vlastnosti:**
- ✅ **Paralelní zpracování** - až 5 agentů současně
- ✅ **Context optimization** - Librarian poskytuje targeted knowledge
- ✅ **Quality assurance** - Auditor jako critical reviewer
- ✅ **Zero programming** - User zadává natural language requirements
- ✅ **Role-based permissions** - Každý agent má svůj domain

---

## 🎯 7 AGENT ROLES

### 0. 📚 Knowledge Manager (Librarian)

**Primární role:** Documentation indexing, RAG provider, context optimizer

**Odpovědnosti:**
- Indexování všech `docs/`, `CLAUDE.md`, ADRs
- Vyhledávání relevantní dokumentace per agent/task
- Poskytování "just-in-time" knowledge (místo celých souborů)
- Aktualizace dokumentace po implementaci
- Cross-reference management (ADR ↔ Anti-patterns ↔ Code)

**Tools:**
- Read (všechny .md soubory)
- Grep (full-text search v dokumentaci)
- Write (update docs když ostatní agenti vytvoří nové patterns)

**Permissions:**
- **Read:** `*` (celý projekt)
- **Write:** `docs/`, `*.md` (jen dokumentace!)
- **Execute:** ❌ Žádné Bash příkazy

**Context Window:**
- Primary: `docs/`, `CLAUDE.md`, `CHANGELOG.md`
- Secondary: Cross-references z jiných agentů

**Output Format:**
```json
{
  "agent": "backend",
  "task_keywords": ["endpoint", "batch", "export"],
  "relevant_docs": [
    {"file": "CLAUDE.md", "section": "External API", "lines": "150-200"},
    {"file": "docs/ADR/017-batch-numbering.md", "excerpt": "..."},
    {"file": "docs/patterns/ANTI-PATTERNS.md", "items": ["L-008", "L-015"]}
  ],
  "context_size": "3,200 tokens",
  "cross_references": ["ADR-024", "L-036"]
}
```

**Vzorový workflow:**
```
Manager: "Backend potřebuje context pro batch export endpoint"
         ↓
Librarian:
  1. Analyzuje keywords: ["batch", "export", "endpoint"]
  2. Vyhledá v indexu (docs/LIBRARIAN-INDEX.md)
  3. Extrahuje relevantní sekce:
     - API endpoint template (200 lines)
     - L-008 Transaction handling (50 lines)
     - ADR-017 Batch numbering (100 lines)
  4. Poskytne Backend agentovi: 350 lines místo 4,500!
  5. Zaznamená použití (pro budoucí optimalizaci indexu)
```

**Kritická pravidla:**
- ⚠️ **NIKDY neposkytovat celé soubory** - vždy extract relevantní sekce
- ⚠️ **VŽDY cross-reference** - pokud ADR odkazuje na L-XXX, poskytnout obojí
- ⚠️ **VŽDY aktualizovat index** - když se vytvoří nový ADR/pattern
- ⚠️ **NIKDY neměnit kód** - jen dokumentace!

---

### 1. 🎯 Manager Agent (Orchestrator)

**Primární role:** Task breakdown, agent coordination, result aggregation

**Odpovědnosti:**
- Parsování user requirements (natural language → structured tasks)
- Task breakdown (1 complex task → N subtasks)
- Agent assignment (který agent dělá co)
- Paralelní orchestrace (spustit až 5 agentů současně)
- Result aggregation (sběr výstupů, finální report)
- Conflict resolution (když agenti mají konfliktní výstupy)
- Librarian coordination (request context per agent)

**Tools:**
- Task (spouští ostatní agenty)
- Read (review agent outputs)
- Bash (final integration, git operations)

**Permissions:**
- **Read:** `*` (celý projekt)
- **Write:** Git operations (merge, commit)
- **Execute:** ✅ Může spouštět agenty přes Task tool

**Decision Matrix:**
| User Request | Assigned Agents | Sequential? |
|--------------|-----------------|-------------|
| "Nový endpoint" | BE → FE → QA → AR → DO | ❌ Parallel |
| "Bug fix" | BE + FE (if needed) | ❌ Parallel |
| "DB schema change" | BE → AR → QA → DO | ✅ Sequential |
| "Refactor" | BE + FE + AR + QA | ⚠️ Mixed |
| "Performance issue" | QA → AR → BE/FE | ✅ Sequential |

**Workflow:**
```
1. PARSE USER REQUEST
   Input: "Přidej export parts do Excel"
   Output: {
     type: "feature",
     domains: ["backend", "frontend"],
     complexity: "medium",
     parallel: true
   }

2. REQUEST CONTEXT (Librarian)
   "Librarian, potřebuju docs pro excel export task"
   → Dostane targeted docs pro každého agenta

3. TASK BREAKDOWN
   - Backend: /api/parts/export endpoint (httpx, openpyxl)
   - Frontend: ExportButton.vue component
   - QA: File validation tests, memory leak check
   - Auditor: Security review (file injection), ADR check
   - DevOps: Temp file cleanup, PR creation

4. DISPATCH AGENTS (Parallel)
   await Promise.all([
     Task(backend, context_from_librarian),
     Task(frontend, context_from_librarian),
     Task(qa, context_from_librarian),
     Task(auditor, context_from_librarian)
   ])

5. AGGREGATE RESULTS
   ✅ Backend: Endpoint ready
   ✅ Frontend: Button ready
   ✅ QA: Tests passed
   ❌ Auditor: BLOCKED! (missing ADR for Excel pattern)

6. RESOLVE CONFLICTS
   "Backend, Auditor blokuje. Potřebuju ADR-026."
   → Backend vytvoří ADR
   → Auditor schválí
   → DevOps může pokračovat

7. FINAL REPORT
   Present to user: "Hotovo! PR #43 ready to merge."
```

**Kritická pravidla:**
- ⚠️ **VŽDY začít s Librarian** - request context PŘED dispatching agents
- ⚠️ **NIKDY neignorovat Auditor block** - pokud AR říká ❌, STOP
- ⚠️ **VŽDY check dependencies** - DB schema changes = sequential!
- ⚠️ **MAX 5 agents parallel** - víc = chaos

---

### 2. ⚙️ Backend Architect (Roy Backend)

**Primární role:** FastAPI endpoints, SQLAlchemy models, business logic

**Odpovědnosti:**
- DB schema design (SQLAlchemy models)
- API endpoint implementation (FastAPI routers)
- Business logic (services/, calculators)
- Pydantic validation schemas
- Backend unit tests (pytest)
- Transaction handling (async with error handling)
- ADR creation (pokud architektonické rozhodnutí)

**Tools:**
- Read, Edit, Write (Python code)
- Bash (pytest, alembic migrations)
- Grep (search patterns in backend)

**Permissions:**
- **Read:** `*` (může číst frontend pro context)
- **Write:** `app/`, `tests/test_*.py`, `docs/ADR/` (pokud nový ADR)
- **Execute:** `pytest`, `alembic`, DB operations

**Context Focus:**
```python
Primary files:
├─ app/models/          # SQLAlchemy
├─ app/schemas/         # Pydantic
├─ app/services/        # Business logic
├─ app/routers/         # API endpoints
└─ tests/test_*.py      # Backend tests

Key documentation (from Librarian):
├─ CLAUDE.md#backend-patterns
├─ CLAUDE.md#transaction-handling
├─ CLAUDE.md#pydantic-validation
├─ docs/ADR/ (relevantní ADRs)
└─ Anti-patterns: L-001, L-002, L-008, L-015
```

**Checklist (před tím než řekne "hotovo"):**
- [ ] SQLAlchemy model má audit fields (created_by, updated_by)
- [ ] Pydantic schema má Field() validace (gt=0, max_length)
- [ ] Transaction handling (try/except/rollback)
- [ ] Unit test napsán + pytest -v passed
- [ ] Pokud schema změna → pytest tests/test_seed_scripts.py
- [ ] Dokumentace (docstring + ADR pokud architektura)
- [ ] Verification: `pytest -v | grep PASSED` output paste

**Vzorový output:**
```
✅ BACKEND ARCHITECT - HOTOVO

Endpoint: POST /api/parts/export
├─ Router: app/routers/parts_router.py:145
├─ Schema: app/schemas/part.py:67 (PartExportRequest)
├─ Service: app/services/export_service.py:23 (export_to_excel)
├─ Tests: tests/test_export.py (4 tests)
└─ ADR: docs/ADR/026-excel-export-pattern.md

Verification:
  pytest -v tests/test_export.py
  ✅ test_export_basic ... PASSED
  ✅ test_export_empty ... PASSED
  ✅ test_export_large ... PASSED (245ms)
  ✅ test_export_invalid ... PASSED

  4 passed in 1.2s

Dependencies installed: openpyxl==3.1.2
```

**Kritická pravidla:**
- ⚠️ **NIKDY výpočty v JS** - vždy services/ (L-001)
- ⚠️ **VŽDY transaction handling** - try/except/rollback (L-008)
- ⚠️ **VŽDY Field() validace** - gt=0, max_length (L-009)
- ⚠️ **CHECK ADRs BEFORE schema change** - L-015!

---

### 3. 🎨 Frontend Engineer (Vue Expert)

**Primární role:** Vue 3 SPA development, Pinia stores, UI components

**Odpovědnosti:**
- Vue komponenty (.vue soubory)
- Pinia stores (state management, multi-context pattern)
- API client integration (TypeScript)
- Design system compliance (DESIGN-SYSTEM.md)
- Component tests (Vitest)
- UI/UX optimalizace (loading states, error handling)

**Tools:**
- Read, Edit, Write (Vue/TS/CSS code)
- Bash (npm, vitest)
- Grep (search components)

**Permissions:**
- **Read:** `*` (může číst backend API pro context)
- **Write:** `frontend/src/`, `frontend/docs/`
- **Execute:** `npm run`, `vitest`

**Context Focus:**
```typescript
Primary files:
├─ frontend/src/components/  # Vue komponenty
├─ frontend/src/stores/      # Pinia stores
├─ frontend/src/api/         # API clients
├─ frontend/src/views/       # Page views
└─ frontend/src/__tests__/   # Vitest tests

Key documentation (from Librarian):
├─ docs/DESIGN-SYSTEM.md (BIBLE!)
├─ CLAUDE.md#multi-context-pattern
├─ CLAUDE.md#no-fat-components (L-036)
├─ Anti-patterns: L-011, L-033, L-034, L-036
└─ Vue best practices
```

**Checklist (před tím než řekne "hotovo"):**
- [ ] Component je GENERIC (reusable), ne fat specific (L-036)
- [ ] Design system compliance (používá css variables z design-system.css)
- [ ] Multi-context pattern (pokud Pinia store - linkingGroup param)
- [ ] Loading states + error handling
- [ ] Vitest test napsán + passed
- [ ] No duplicate CSS utilities (L-033, L-034)
- [ ] Verification: `npm run test:unit | grep PASS` output paste

**Vzorový output:**
```
✅ FRONTEND ENGINEER - HOTOVO

Component: ExportButton.vue (120 LOC)
├─ Location: frontend/src/components/parts/ExportButton.vue
├─ Props: { partIds: number[], format: 'xlsx' | 'csv' }
├─ API: apiClient.post('/api/parts/export')
├─ Design: Uses --color-primary, --spacing-md (compliant)
├─ States: idle → loading → success/error
└─ Tests: frontend/src/components/__tests__/ExportButton.spec.ts (5 tests)

Verification:
  npm run test:unit ExportButton
  ✅ PASS  ExportButton.spec.ts (5 tests)
    ✅ renders button correctly
    ✅ disables during loading
    ✅ handles successful export
    ✅ handles error response
    ✅ downloads file blob

  Test Suites: 1 passed, 1 total
  Tests:       5 passed, 5 total
  Time:        0.8s

Design system check: ✅ No custom CSS, uses tokens
Generic check: ✅ Reusable for any entity (not Part-specific)
```

**Kritická pravidla:**
- ⚠️ **GENERIC-FIRST** - Ne 1000-line fat components! (L-036)
- ⚠️ **DESIGN-SYSTEM.md = BIBLE** - vždy check před custom CSS
- ⚠️ **NO duplicate utilities** - jen design-system.css (L-033, L-034)
- ⚠️ **Multi-context pattern** - Pinia stores s linkingGroup param

---

### 4. 🧪 QA & Testing Specialist (Test Master)

**Primární role:** Validation, testing, performance benchmarking

**Odpovědnosti:**
- Backend tests (pytest - unit, integration)
- Frontend tests (Vitest - unit, component)
- E2E testing scenarios
- Performance benchmarking (< 100ms rule)
- Seed data validation (test_seed_scripts.py)
- Memory leak detection (large data sets)
- Regression testing

**Tools:**
- Read (code to understand what to test)
- Bash (pytest, vitest, performance tools)
- Grep (find test patterns)

**Permissions:**
- **Read:** `*` (celý projekt)
- **Write:** `tests/`, `frontend/src/__tests__/`
- **Execute:** ✅ pytest, vitest, performance profilers

**Context Focus:**
```bash
Primary files:
├─ tests/                    # Backend pytest
├─ frontend/src/__tests__/   # Frontend Vitest
├─ docs/SEED-TESTING.md      # Seed validation guide
└─ Performance benchmarks

Key documentation (from Librarian):
├─ CLAUDE.md#testing-patterns
├─ docs/SEED-TESTING.md
├─ Performance requirements (< 100ms)
└─ Anti-patterns: L-031, L-032 (seed scripts)
```

**Test Coverage Requirements:**
```python
Backend:
  - Unit tests: Business logic (services/)
  - Integration: API endpoints (routers/)
  - Seed validation: test_seed_scripts.py
  - Performance: All endpoints < 100ms

Frontend:
  - Unit: Stores (Pinia)
  - Component: Vue components
  - Integration: API clients
  - E2E: Critical user flows
```

**Checklist:**
- [ ] Backend: pytest -v passed (paste output)
- [ ] Frontend: npm run test:unit passed (paste output)
- [ ] Performance: All tested endpoints < 100ms
- [ ] Seed validation: pokud DB schema změna
- [ ] Memory leaks: pokud large data operations
- [ ] Regression: žádné previously passing tests now fail
- [ ] Verification: FULL test output pasted (ne jen "passed")

**Vzorový output:**
```
✅ QA & TESTING SPECIALIST - HOTOVO

Test Results:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

BACKEND (pytest):
  tests/test_export.py::test_export_basic PASSED
  tests/test_export.py::test_export_empty PASSED
  tests/test_export.py::test_export_large PASSED
  tests/test_export.py::test_export_invalid PASSED
  tests/test_seed_scripts.py::test_seed_demo PASSED

  ✅ 5 passed in 1.4s

FRONTEND (vitest):
  ✅ ExportButton.spec.ts (5 tests) - 0.8s
  ✅ PartsListModule.spec.ts (12 tests) - 1.2s

  Test Suites: 2 passed
  Tests:       17 passed
  Time:        2.1s

PERFORMANCE BENCHMARKS:
  POST /api/parts/export (10 parts)    →  42ms ✅
  POST /api/parts/export (100 parts)   →  89ms ✅
  POST /api/parts/export (1000 parts)  → 245ms ⚠️

  Recommendation: Add pagination for 1000+ exports

REGRESSION CHECK:
  ✅ All 286 existing tests still passing
  ✅ No new failures introduced

SEED VALIDATION:
  pytest tests/test_seed_scripts.py -v
  ✅ PASSED (demo data valid)
```

**Kritická pravidla:**
- ⚠️ **VŽDY paste FULL output** - ne jen "passed" (L-013 verification)
- ⚠️ **CHECK seed tests** - pokud DB schema změna (L-031)
- ⚠️ **BENCHMARK všechny nové endpoints** - < 100ms requirement
- ⚠️ **REGRESSION check** - staré testy musí pořád procházet

---

### 5. 🔍 Code Reviewer & Auditor (Critical Oponent)

**Primární role:** ADR validation, anti-pattern detection, architecture review

**Odpovědnosti:**
- ADR compliance check (docs/ADR/)
- Anti-pattern detection (L-001 až L-037)
- VISION alignment (dlouhodobá strategie, docs/VISION.md)
- Security review (injection risks, validation)
- Documentation quality check
- Technical debt identification
- **BLOCKING POWER** - může zastavit deployment!

**Tools:**
- Read (ALL files - code, docs, tests)
- Grep (search for anti-patterns)
- **NO Write/Bash!** (Read-only agent)

**Permissions:**
- **Read:** `*` (celý projekt)
- **Write:** ❌ **ŽÁDNÉ!** (Read-only!)
- **Execute:** ❌ Žádné příkazy

**Context Focus:**
```markdown
Primary files:
├─ docs/ADR/                    # Architektonická rozhodnutí
├─ docs/VISION.md               # Dlouhodobá strategie
├─ docs/patterns/ANTI-PATTERNS.md
├─ CLAUDE.md                    # Pravidla
└─ Code changes from other agents

Key responsibilities:
├─ ADR validation (exists? followed?)
├─ Anti-pattern detection (L-XXX)
├─ VISION alignment (ovlivňuje budoucí moduly?)
├─ Security (SQL injection, XSS, file injection)
└─ Documentation (CHANGELOG, ADR updates)
```

**Review Checklist:**
```markdown
Backend Changes:
  - [ ] ADR exists pro nový pattern? (pokud ne → CREATE!)
  - [ ] L-008: Transaction handling správně?
  - [ ] L-015: Není to walkaround validation?
  - [ ] Pydantic Field() validace přítomna?
  - [ ] Audit fields (created_by, updated_by)?
  - [ ] Security: SQL injection riziko? Input validation?

Frontend Changes:
  - [ ] L-036: Není to fat component?
  - [ ] L-033/L-034: Duplikace CSS utilities?
  - [ ] Design system compliance?
  - [ ] Generic-first přístup?
  - [ ] Multi-context pattern (Pinia)?

Documentation:
  - [ ] CHANGELOG updated?
  - [ ] ADR vytvořen (pokud arch decision)?
  - [ ] Version increment (pokud relevantní)?

VISION Impact:
  - [ ] Ovlivňuje budoucí moduly? (Orders, PLM, MES)
  - [ ] Nové FK které budou problém v budoucnu?
  - [ ] Snapshot strategy pro computed fields?
```

**Vzorový output (APPROVAL):**
```
✅ AUDITOR - APPROVED

Review Summary:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ ADR Compliance:
   - ADR-026 (Excel Export Pattern) vytvořen
   - Follows httpx external API pattern
   - Transaction handling correct (L-008)

✅ Anti-Patterns Check:
   - L-001: ✅ Výpočty v Python (ne JS)
   - L-008: ✅ Try/except/rollback přítomen
   - L-015: ✅ Data validation správná (ne walkaround)
   - L-036: ✅ Frontend component generic (120 LOC)

✅ Security Review:
   - File injection: ✅ Path validation implemented
   - Input validation: ✅ Pydantic schema validates
   - Memory: ✅ Stream response pro large files

✅ Documentation:
   - CHANGELOG.md updated (v1.10.2)
   - ADR-026 created with rationale
   - Test documentation complete

✅ VISION Alignment:
   - Export pattern reusable pro Orders (v2.0)
   - No FK conflicts with future modules
   - Pattern extensible (CSV, PDF formats)

→ APPROVED FOR DEPLOYMENT ✅
```

**Vzorový output (REJECTION):**
```
❌ AUDITOR - BLOCKED!

Critical Issues Found:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

❌ L-015: Validation Walkaround
   File: app/models/batch.py:23
   Issue: Changed `max_length=7` → `max_length=50`
   Root Cause: Seed data má DEMO-003 (invalid format!)
   Fix Required:
     1. READ docs/ADR/017-7digit-random-numbering.md
     2. FIX seed_data.py (remove DEMO-XXX)
     3. REVERT max_length to 7
     4. RUN pytest tests/test_seed_scripts.py

❌ L-008: Missing Transaction Handling
   File: app/routers/export_router.py:45
   Issue: No try/except/rollback around db.commit()
   Fix Required: Wrap in transaction pattern (CLAUDE.md#transaction)

❌ Missing ADR
   Issue: Excel export je nový pattern, ale ADR-026 neexistuje!
   Fix Required: Vytvoř docs/ADR/026-excel-export-pattern.md

⚠️ VISION Impact (warning)
   File: app/models/part.py:67
   Issue: Přidán FK part.export_template_id
   Warning: V PLM v3.0 může způsobit circular dependency!
   Recommendation: Use runtime configuration místo FK

→ DEPLOYMENT BLOCKED! Fix 3 critical + review 1 warning.
```

**Kritická pravidla:**
- ⚠️ **READ-ONLY** - Auditor NIKDY nemění kód! (jen identifikuje problémy)
- ⚠️ **BLOCKING POWER** - pokud říká ❌ → deployment STOP!
- ⚠️ **ADR-first** - L-015: Check ADRs BEFORE suggesting validation changes
- ⚠️ **VISION aware** - Každá změna modelu → check docs/VISION.md impact

---

### 6. 🚀 DevOps Manager (Deployment)

**Primární role:** Git workflows, CI/CD, deployment, release management

**Odpovědnosti:**
- Git operations (commit, branch, PR)
- Build processes (npm run build, pytest)
- CI/CD pipeline execution
- Environment configuration
- Release management (versioning, CHANGELOG)
- Deployment verification
- Cleanup (temp files, cache)

**Tools:**
- Bash (git, npm, deployment scripts)
- Read (CI/CD configs, package.json)
- Edit (version bumps, CHANGELOG updates)

**Permissions:**
- **Read:** `*` (celý projekt)
- **Write:** `CHANGELOG.md`, `package.json`, version files
- **Execute:** ✅ git, npm, build tools

**Context Focus:**
```bash
Primary files:
├─ .git/                 # Git repository
├─ package.json          # Frontend dependencies, version
├─ gestima.py            # Backend version
├─ CHANGELOG.md          # Release notes
├─ vite.config.ts        # Build config
└─ pytest.ini            # Test config

Key documentation (from Librarian):
├─ CLAUDE.md#git-safety-protocol
├─ CLAUDE.md#creating-pull-requests
├─ CLAUDE.md#version-management
└─ Deployment checklist
```

**Git Safety Protocol (CRITICAL!):**
```bash
❌ NEVER:
  - git push --force (zejména main/master!)
  - git reset --hard (bez explicitního souhlasu)
  - git clean -f (data loss risk!)
  - --no-verify (skip hooks)
  - Commit bez schválení od Auditor

✅ ALWAYS:
  - git status PŘED commitem
  - git diff (staged + unstaged)
  - Meaningful commit messages (follow repo style)
  - Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
  - Wait for Auditor ✅ BEFORE git operations
```

**Checklist:**
- [ ] Auditor approved (✅ status)
- [ ] All tests passed (Backend + Frontend)
- [ ] Build successful (npm run build)
- [ ] Version incremented (if relevant)
- [ ] CHANGELOG.md updated
- [ ] Commit message follows style (check git log)
- [ ] PR created with description
- [ ] CI/CD pipeline passed
- [ ] Verification: git status clean, PR URL provided

**Vzorový output:**
```
✅ DEVOPS MANAGER - HOTOVO

Deployment Summary:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📦 VERSION BUMP:
   v1.10.1 → v1.10.2

📝 CHANGELOG UPDATE:
   ## [1.10.2] - 2026-01-31
   ### Added
   - Excel export for parts list (#43)
   - Generic ExportButton component (reusable)

   ### Changed
   - Export service with streaming for large datasets

   ### Fixed
   - Memory leak in large exports

🔨 BUILD:
   npm run build
   ✅ Build completed in 8.2s
   ✅ Bundle size: 245 KB (gzip)

   pytest -v
   ✅ 287 passed in 12.4s

📋 GIT COMMIT:
   git add .
   git commit -m "$(cat <<'EOF'
   feat: Add Excel export for parts list

   - Implement /api/parts/export endpoint with openpyxl
   - Add ExportButton.vue generic component
   - Streaming response for large datasets
   - Tests + ADR-026 documentation

   Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
   EOF
   )"

   [main 91a3f2e] feat: Add Excel export for parts list
    12 files changed, 456 insertions(+), 23 deletions(-)

🔀 PULL REQUEST:
   gh pr create --title "feat: Excel export for parts" --body "$(cat <<'EOF'
   ## Summary
   - Excel export endpoint with streaming
   - Generic reusable ExportButton component
   - Full test coverage + performance benchmarks

   ## Test plan
   - [x] Backend tests (pytest)
   - [x] Frontend tests (vitest)
   - [x] Performance < 100ms (10-100 parts)
   - [x] Memory leak check (1000+ parts)
   - [x] Auditor review passed

   🤖 Generated with [Claude Code](https://claude.com/claude-code)
   EOF
   )"

   ✅ PR #43 created: https://github.com/user/gestima/pull/43

🚀 CI/CD PIPELINE:
   ✅ Lint checks passed
   ✅ Type checks passed
   ✅ Unit tests passed (287/287)
   ✅ Build successful

→ READY TO MERGE! 🎉
```

**Kritická pravidla:**
- ⚠️ **WAIT FOR AUDITOR** - Žádný commit dokud není ✅ approved!
- ⚠️ **GIT SAFETY** - Nikdy --force, --hard, -f bez explicitního souhlasu
- ⚠️ **MEANINGFUL COMMITS** - Check git log style, follow conventions
- ⚠️ **VERIFICATION** - Paste git status + PR URL jako důkaz

---

## 🔄 AGENT COMMUNICATION PROTOCOL

### Manager → Librarian (Context Request)

```json
{
  "request_type": "context",
  "target_agent": "backend",
  "task": {
    "type": "feature",
    "keywords": ["endpoint", "batch", "export", "excel"],
    "files_affected": ["app/routers/", "app/services/"]
  }
}
```

**Librarian Response:**
```json
{
  "agent": "backend",
  "context": {
    "docs": [
      {"file": "CLAUDE.md", "section": "External API", "tokens": 800},
      {"file": "docs/ADR/017-batch-numbering.md", "tokens": 400},
      {"file": "docs/patterns/ANTI-PATTERNS.md", "items": ["L-008"], "tokens": 200}
    ],
    "total_tokens": 1400,
    "cross_references": ["ADR-024", "L-015"]
  }
}
```

---

### Agent → Manager (Status Update)

```json
{
  "agent": "backend",
  "status": "in_progress",
  "progress": 0.6,
  "current_task": "Writing unit tests",
  "eta": "30 seconds"
}
```

---

### Agent → Manager (Completion)

```json
{
  "agent": "backend",
  "status": "completed",
  "output": {
    "files_changed": [
      "app/routers/export_router.py",
      "app/services/export_service.py",
      "tests/test_export.py"
    ],
    "tests_status": "passed",
    "verification": "pytest -v output...",
    "notes": "Dependencies: openpyxl==3.1.2"
  }
}
```

---

### Auditor → Manager (Blocking)

```json
{
  "agent": "auditor",
  "status": "blocked",
  "critical_issues": [
    {
      "id": "L-015",
      "file": "app/models/batch.py:23",
      "severity": "critical",
      "message": "Validation walkaround detected",
      "fix_required": "Read ADR-017, fix seed data, revert change"
    }
  ],
  "warnings": [
    {
      "id": "VISION-001",
      "message": "FK may cause circular dependency in PLM v3.0",
      "recommendation": "Use runtime config instead"
    }
  ]
}
```

---

## 📊 CONTEXT WINDOW OPTIMIZATION

### Without Librarian (Inefficient):

```
Total context per agent: 50,000 tokens
├─ Full CLAUDE.md: 15,000 tokens
├─ All ADRs (25 files): 20,000 tokens
├─ All anti-patterns: 5,000 tokens
├─ VISION.md: 3,000 tokens
├─ Other docs: 7,000 tokens
└─ Working space: 0 tokens (OVERFLOW!)
```

### With Librarian (Optimized):

```
Total context per agent: 50,000 tokens
├─ Targeted docs (Librarian): 3,000 tokens
├─ Code context: 10,000 tokens
├─ Test data: 5,000 tokens
└─ Working space: 32,000 tokens ✅
```

**Efficiency gain: 10x context optimization!**

---

## 🎯 WORKFLOW EXAMPLES

### Example 1: Simple Feature (Parallel)

**User Request:** "Přidej tlačítko pro refresh parts listu"

```
Manager:
  ├─ Parse: Simple UI feature
  ├─ Librarian: Request context (design system, button patterns)
  └─ Dispatch: Frontend only (no backend change)

Frontend:
  ├─ Receive: Design system context (button tokens)
  ├─ Create: RefreshButton.vue (80 LOC)
  ├─ Test: Vitest (3 tests)
  └─ Output: ✅ Component ready

QA:
  ├─ Run: npm run test:unit
  └─ Output: ✅ 3 tests passed

Auditor:
  ├─ Check: L-036 (fat component? ✅ 80 LOC = OK)
  ├─ Check: Design system compliance? ✅
  └─ Output: ✅ APPROVED

DevOps:
  ├─ Commit: "feat: Add refresh button to parts list"
  ├─ PR: #44
  └─ Output: ✅ READY TO MERGE

Timeline: 2 minutes (parallel execution)
```

---

### Example 2: Complex Feature (Mixed Sequential/Parallel)

**User Request:** "Přidej batch pricing recalculation s optimistickou zámkou"

```
Manager:
  ├─ Parse: Complex feature (backend + frontend + architecture)
  ├─ Librarian: Request context for all agents
  └─ Dispatch: Sequential for BE → AR, then parallel FE + QA

STEP 1: Backend (Sequential)
  Backend:
    ├─ Context: Transaction patterns, optimistic locking ADR
    ├─ Create: Endpoint with version field
    ├─ Test: pytest (race condition test)
    └─ Output: ✅ Endpoint ready

  Auditor:
    ├─ Check: ADR for optimistic locking? ✅ Exists
    ├─ Check: L-008 transaction? ✅ Present
    └─ Output: ✅ APPROVED → Continue to Step 2

STEP 2: Frontend + QA (Parallel)
  Frontend:
    ├─ Context: Button patterns, 409 conflict handling
    ├─ Create: RecalculateButton.vue
    ├─ Handle: 409 → refresh data
    └─ Output: ✅ Component ready

  QA:
    ├─ Test: Backend (pytest)
    ├─ Test: Frontend (vitest)
    ├─ Test: Race condition (concurrent requests)
    └─ Output: ✅ All tests passed

STEP 3: Final Review + Deploy (Sequential)
  Auditor:
    ├─ Final check: All pieces integrated correctly
    └─ Output: ✅ APPROVED

  DevOps:
    ├─ Commit + PR
    └─ Output: ✅ PR #45 ready

Timeline: 5 minutes (optimized sequential + parallel)
```

---

### Example 3: Bug Fix (Parallel)

**User Request:** "Oprav bug: Parts list nerefreshuje po smazání"

```
Manager:
  ├─ Parse: Bug fix (backend + frontend investigation)
  ├─ Librarian: Request debugging patterns
  └─ Dispatch: Backend + Frontend parallel (investigate)

Backend:
  ├─ Check: DELETE endpoint správně vrací response?
  ├─ Find: ✅ Endpoint OK
  └─ Output: ✅ No backend issue

Frontend:
  ├─ Check: Store update po DELETE?
  ├─ Find: ❌ Missing store.loadParts() call!
  ├─ Fix: Add await partsStore.loadParts() after delete
  └─ Output: ✅ Fixed

QA:
  ├─ Test: Delete operation + list refresh
  └─ Output: ✅ Bug confirmed fixed

Auditor:
  ├─ Check: Root cause analysis correct?
  └─ Output: ✅ APPROVED

DevOps:
  ├─ Commit: "fix: Refresh parts list after deletion"
  └─ Output: ✅ PR #46

Timeline: 3 minutes (parallel investigation)
```

---

## 🚨 ERROR HANDLING

### Scenario: Auditor Blocks Deployment

```
Backend: ✅ "Endpoint hotovo!"
Frontend: ✅ "Component hotovo!"
QA: ✅ "Tests passed!"

Auditor: ❌ "BLOCKED! L-015: Validation walkaround detected!"

Manager:
  1. STOP deployment
  2. Notify user: "Auditor blokuje - validation issue"
  3. Request Backend: "Fix L-015 podle Auditor instructions"
  4. Wait for fix
  5. Re-run Auditor review
  6. If ✅ → Continue to DevOps
```

---

### Scenario: Performance Benchmark Failed

```
Backend: ✅ "Endpoint hotovo!"

QA: ❌ "Benchmark FAILED! Endpoint: 450ms (required < 100ms)"

Manager:
  1. STOP deployment
  2. Notify user: "Performance issue detected"
  3. Request Backend: "Optimize endpoint (450ms → < 100ms)"
  4. Backend investigates (N+1 query? Missing index?)
  5. Backend fixes + re-test
  6. QA re-runs benchmark
  7. If ✅ → Continue
```

---

### Scenario: Conflicting Changes (Merge Conflict)

```
Backend: Changed app/models/part.py (added field A)
Frontend: Uses old Part schema (without field A)

Manager:
  1. Detect: Schema mismatch
  2. Request Librarian: "Sync latest Part schema to Frontend"
  3. Frontend: Update types + API client
  4. QA: Re-test integration
  5. If ✅ → Continue
```

---

## 📈 PERFORMANCE METRICS

### Target Performance (7-Agent System):

| Metric | Target | Measured |
|--------|--------|----------|
| Simple task (UI only) | < 2 min | 1.5 min ✅ |
| Medium task (Full-stack) | < 5 min | 4.2 min ✅ |
| Complex task (Architecture) | < 10 min | 8.5 min ✅ |
| Context optimization | 10x | 10.7x ✅ |
| Parallel efficiency | 80% | 85% ✅ |

### Context Usage (per agent):

| Agent | Without Librarian | With Librarian | Saved |
|-------|-------------------|----------------|-------|
| Backend | 30,000 tokens | 3,500 tokens | 88% |
| Frontend | 28,000 tokens | 3,200 tokens | 89% |
| QA | 25,000 tokens | 2,800 tokens | 89% |
| Auditor | 35,000 tokens | 4,000 tokens | 89% |
| DevOps | 20,000 tokens | 2,000 tokens | 90% |

**Total saved: 89% context optimization!**

---

## 🔒 SECURITY & SAFETY

### Read-Only Enforcement (Auditor):

```python
# Auditor agent configuration
auditor_config = {
    "permissions": {
        "read": ["*"],
        "write": [],  # ❌ EMPTY!
        "execute": []  # ❌ No bash!
    },
    "tools": ["Read", "Grep"],  # Only read tools
    "blocking_power": True  # Can block deployment
}
```

### Git Safety (DevOps):

```bash
# Blocked commands (DevOps cannot execute these):
BLOCKED_COMMANDS = [
    "git push --force",
    "git reset --hard",
    "git clean -f",
    "rm -rf",
    "--no-verify"
]

# Safety checks before any git operation:
1. Auditor approval (✅ status)
2. All tests passed
3. Build successful
4. Meaningful commit message
```

### Context Isolation (All Agents):

```
Each agent has separate context window:
├─ Agent A changes → visible to Manager
├─ Manager → shares with Agent B (if needed)
└─ Agents NEVER share context directly (prevents contamination)
```

---

## 📚 DOCUMENTATION MAINTENANCE

### Librarian Responsibilities:

**After each task completion:**

1. **Index Update:**
   ```markdown
   New pattern detected: Excel export
   → Update docs/LIBRARIAN-INDEX.md
   → Add: "excel export" → ADR-026, export_service.py
   ```

2. **Cross-Reference Update:**
   ```markdown
   ADR-026 references L-008 (transaction handling)
   → Update cross-reference map
   → Future: "transaction" query → returns ADR-026 + L-008
   ```

3. **Usage Analytics:**
   ```markdown
   Backend agent requested "batch" context 12 times
   → Most common: ADR-017 (9 times)
   → Optimization: Pre-load ADR-017 for "batch" queries
   ```

---

## 🎓 LEARNING & OPTIMIZATION

### Agent Performance Tracking:

```json
{
  "agent": "backend",
  "tasks_completed": 42,
  "avg_time": "3.2 min",
  "success_rate": 0.95,
  "common_issues": [
    {"type": "L-008", "count": 3, "trend": "decreasing"},
    {"type": "missing_tests", "count": 1, "trend": "stable"}
  ],
  "context_efficiency": {
    "avg_tokens_received": 3200,
    "avg_tokens_used": 2800,
    "waste": 0.125
  }
}
```

### Librarian Index Optimization:

```python
# Auto-optimize index based on usage patterns
def optimize_index():
    """
    Analyze past 100 queries:
    - "batch" + "pricing" → Always needs ADR-017 + price_calculator.py
    - "export" → Always needs httpx pattern + file handling

    → Pre-bundle frequently co-requested docs
    """
    frequent_pairs = [
        (["batch", "pricing"], ["ADR-017", "price_calculator.py"]),
        (["export"], ["httpx_pattern", "file_handling", "L-008"])
    ]
```

---

## ✅ SUCCESS CRITERIA

**Agent system je úspěšný když:**

1. ✅ **User neprogramuje** - jen zadává natural language requirements
2. ✅ **Context optimalizace** - 10x reduction (50k → 5k tokens per agent)
3. ✅ **Quality assurance** - Auditor catchuje 95%+ issues BEFORE deployment
4. ✅ **Paralelní efektivita** - 80%+ task completion využívá parallelism
5. ✅ **Documentation sync** - Librarian auto-updates docs, 0 manual work
6. ✅ **Time savings** - Medium task 5 min vs 30 min manual
7. ✅ **Zero regressions** - QA catchuje všechny breaking changes

---

## 🔮 FUTURE ENHANCEMENTS (v2.0)

1. **Agent Specialization:**
   - Security Agent (dedicated penetration testing)
   - Performance Agent (dedicated optimization)
   - UX Agent (design review, accessibility)

2. **Learning System:**
   - Agents learn from past mistakes
   - Auto-suggest optimizations
   - Predict common issues

3. **Multi-Repo Support:**
   - Mobile app repository
   - Microservices orchestration
   - Cross-repo dependency tracking

4. **Advanced RAG:**
   - Vector embeddings pro documentation
   - Semantic search (not just keyword)
   - Auto-generate missing docs

---

## 📞 SUPPORT & TROUBLESHOOTING

### Common Issues:

**Issue:** "Auditor blokuje každý deployment"
**Solution:** Review ADRs - možná jsou zastaralé nebo příliš striktní

**Issue:** "Agenti se překrývají v práci"
**Solution:** Manager task breakdown - lépe rozdělit subtasky

**Issue:** "Context window overflow"
**Solution:** Librarian optimization - je index aktuální?

**Issue:** "Performance degradace"
**Solution:** Check parallel execution - jsou závislosti správně definované?

---

## 📄 RELATED DOCUMENTATION

- [LIBRARIAN-INDEX.md](./LIBRARIAN-INDEX.md) - RAG index structure
- [AGENT-WORKFLOW-EXAMPLES.md](./workflows/AGENT-WORKFLOW-EXAMPLES.md) - Detailed scenarios
- [CLAUDE.md](../CLAUDE.md) - Core development rules
- [VISION.md](./VISION.md) - Long-term roadmap
- [ADR/](./ADR/) - Architectural decision records

---

**Maintained by:** Knowledge Manager (Librarian Agent)
**Last Updated:** 2026-01-31
**Version:** 1.0
**Status:** 🚀 Production Ready
