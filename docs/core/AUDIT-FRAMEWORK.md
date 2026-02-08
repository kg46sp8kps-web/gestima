# GESTIMA AUDIT FRAMEWORK

**Version:** 1.0 (2026-02-08)
**Purpose:** Comprehensive audit checklist for version milestones - TOTÁLNÍ JISTOTA před verzí

---

## 🎯 AUDIT TYPES & TRIGGERS

| Audit Type | Trigger | Agent | Priority | Output Location |
|------------|---------|-------|----------|-----------------|
| **POST-CLEANUP** | After 100+ LOC deleted | Auditor (Opus) | MANDATORY | `docs/audits/YYYY-MM-DD-cleanup-audit.md` |
| **POST-FEATURE** | After feature completion (3+ files) | Auditor (Opus) | MANDATORY | `docs/audits/YYYY-MM-DD-feature-audit.md` |
| **POST-MIGRATION** | After Alembic migration | Auditor (Opus) | MANDATORY | `docs/audits/YYYY-MM-DD-migration-audit.md` |
| **PRE-RELEASE** | Before git tag vX.Y.Z | Auditor (Opus) | **BLOCKING** | `docs/audits/YYYY-MM-DD-pre-release-audit.md` |

**CRITICAL:** PRE-RELEASE audit je **BLOCKING** - žádný tag bez APPROVED audit!

---

## 📋 COMPREHENSIVE AUDIT CHECKLIST (8 sekčí)

### SECTION 1: Code Quality ⚙️

#### 1.1 Dead Code Detection
- [ ] **Orphaned imports** - žádné `import` smazaných modulů
  ```bash
  grep -r "from app.services.deleted_module" app/
  ```
- [ ] **Unused components** - Vue komponenty bez `import` reference
  ```bash
  for f in frontend/src/components/**/*.vue; do
    name=$(basename $f .vue)
    grep -r "import.*$name" frontend/src/ || echo "ORPHAN: $f"
  done
  ```
- [ ] **Commented code blocks** - žádné bloky >10 řádků zakomentovaného kódu

#### 1.2 DRY Violations
- [ ] **Duplicate CSS** - kontrola `.btn`, `.badge`, utilities mimo `design-system.css`
  ```bash
  grep -r "\.btn\s*{" frontend/src/components/ frontend/src/views/
  ```
- [ ] **Duplicate logic** - service funkcionalita zduplikována v routeru
- [ ] **Hardcoded values** - colors, spacing, font-sizes mimo CSS vars
  ```bash
  grep -rE "(#[0-9a-fA-F]{3,6}|[0-9]+px|font-size:\s*[0-9])" frontend/src/components/
  ```

#### 1.3 Anti-Pattern Compliance (L-XXX)
- [ ] **L-008:** Transaction handling - všechny `db.commit()` v try/except
- [ ] **L-009:** Pydantic Field() validace - žádné holé typy v schemas
- [ ] **L-036:** Component LOC - žádná komponenta >300 LOC
- [ ] **L-042:** Žádné secrets/credentials v kódu
- [ ] **L-043:** Žádné bare `except:` nebo `except...pass`
- [ ] **L-044:** Žádné `print()`, `console.log()`, `debugger` v produkci
- [ ] **L-049:** Žádný TypeScript `any` typ

#### 1.4 Complexity Metrics
- [ ] **Python files** - žádný soubor >800 LOC (ideálně <500)
- [ ] **Vue components** - žádný >300 LOC
- [ ] **Cyclomatic complexity** - funkce <10 branches (manual review kritických funkcí)

---

### SECTION 2: Test Coverage 🧪

#### 2.1 Unit Test Existence
- [ ] **Backend:** Každý `app/routers/*_router.py` má `tests/test_*_router.py`
- [ ] **Backend:** Každý `app/services/*_service.py` má `tests/test_*_service.py`
- [ ] **Frontend:** Kritické composables mají `.spec.ts` (minimum: useMachiningTimeEstimation, useAuth, usePricing)

#### 2.2 Test Quality
- [ ] **Happy path** - základní CRUD operace pokryté
- [ ] **Edge cases** - 404, 409, 422 error responses testované
- [ ] **Auth/AuthZ** - protected routes vyžadují auth
- [ ] **Data integrity** - FK constraints, soft delete cascade testované

#### 2.3 Test Execution
- [ ] **Backend:** `pytest` PASS - 0 failures
  ```bash
  cd /Users/lofas/Documents/__App_Claude/Gestima && pytest -v
  ```
- [ ] **Frontend:** `vitest` PASS - 0 failures
  ```bash
  cd frontend && npm run test
  ```
- [ ] **Coverage:** Backend ≥70%, Frontend ≥60% (estimated)

---

### SECTION 3: Architecture Compliance 🏗️

#### 3.1 ADR Adherence
- [ ] **ADR existence** - nová architektonická rozhodnutí mají ADR
- [ ] **ADR implementation** - implementace odpovídá ADR specifikaci
- [ ] **ADR index** - `docs/ADR/README.md` aktualizován

#### 3.2 Design System Compliance
- [ ] **CSS tokens** - všechny barvy přes `var(--color-*)`, spacing přes `var(--space-*)`
- [ ] **Lucide icons** - žádné emoji v produkční UI (L-038)
- [ ] **Typography** - font-size přes `var(--text-*)` tokens

#### 3.3 Module Structure
- [ ] **Floating Windows** - nové UI komponenty jako `*Module.vue`, NE `*View.vue`
- [ ] **Split-pane pattern** - ListModule → ListPanel + DetailPanel
- [ ] **Generic-first** - reusable komponenty <300 LOC, specializace přes props

#### 3.4 Layer Separation
- [ ] **Business logic** - výpočty POUZE v Python `services/`, NE v JS (L-001)
- [ ] **Routing** - routers pouze orchestrace, business logic v services
- [ ] **Presentation** - Vue komponenty pouze rendering, state v Pinia stores

---

### SECTION 4: Security 🔒

#### 4.1 OWASP Top 10
- [ ] **A01: Broken Access Control** - všechny protected endpointy mají `get_current_user` / `require_role`
- [ ] **A02: Cryptographic Failures** - žádné plaintext passwords, sensitive data encrypted
- [ ] **A03: Injection** - Pydantic validace, SQLAlchemy parametrizované queries (NE string concat)
- [ ] **A04: Insecure Design** - soft delete místo hard delete, audit trail přítomný
- [ ] **A05: Security Misconfiguration** - CORS správně nakonfigurován, žádné debug mode v prod

#### 4.2 Authentication & Authorization
- [ ] **Auth check** - žádný endpoint bez `current_user: User = Depends(get_current_user)`
- [ ] **Role check** - admin-only endpointy mají `require_role([UserRole.ADMIN])`
- [ ] **JWT validation** - token expiration a signature verification

#### 4.3 Input Validation
- [ ] **Pydantic schemas** - všechna pole mají Field() s constraints (gt, ge, max_length, pattern)
- [ ] **SQL injection** - SQLAlchemy ORM, žádné raw SQL queries
- [ ] **XSS protection** - Vue auto-escaping, žádné `v-html` s user input

#### 4.4 Secrets Management
- [ ] **No hardcoded secrets** - API keys, passwords v `.env`, NE v kódu
- [ ] **Git history** - žádné secrets v git history (check `.env.example` vs `.env`)

---

### SECTION 5: Performance ⚡

#### 5.1 Database Queries
- [ ] **N+1 detection** - žádné `await db.get()` v loopu (use `selectinload`)
- [ ] **Index coverage** - FK sloupce mají index
- [ ] **Query optimization** - `limit()` na large collections

#### 5.2 API Response Times
- [ ] **Async patterns** - všechny I/O operace async (db, file, network)
- [ ] **Pagination** - large collections (>100 items) paginované
- [ ] **Caching** - opakované queries cachované (future)

#### 5.3 Frontend Performance
- [ ] **Bundle size** - `npm run build` PASS, žádné warnings
  ```bash
  cd frontend && npm run build
  ```
- [ ] **Lazy loading** - large komponenty lazy-loaded
- [ ] **Debounce** - search inputs debounced (300ms)

#### 5.4 Large Files Audit
- [ ] **Backend:** Žádný Python soubor >800 LOC (target: <500)
- [ ] **Frontend:** Žádná Vue komponenta >300 LOC
- [ ] **Refactoring plan** - velké soubory mají split-plan v backlog

---

### SECTION 6: Database Integrity 🗄️

#### 6.1 Migration Chain
- [ ] **Linear chain** - žádné merge conflicts v migrations
- [ ] **Up/down migrace** - `alembic upgrade head` && `alembic downgrade -1` PASS
- [ ] **Data migration** - migration obsahuje data transform pokud schema change vyžaduje

#### 6.2 Constraints
- [ ] **FK ondelete** - všechny `ForeignKey()` mají `ondelete="CASCADE|RESTRICT|SET NULL"`
- [ ] **Unique constraints** - partial unique pro soft delete:
  ```sql
  CREATE UNIQUE INDEX ix_parts_part_number_active
  ON parts(part_number) WHERE deleted_at IS NULL;
  ```
- [ ] **CHECK constraints** - enum validace, positive quantities
  ```python
  __table_args__ = (
      CheckConstraint("status IN ('draft', 'active')", name='ck_status'),
      CheckConstraint('quantity > 0', name='ck_quantity_positive'),
  )
  ```

#### 6.3 Data Integrity (Defense in Depth)
- [ ] **L1: DB Constraints** - ondelete, unique, CHECK definované
- [ ] **L2: Pydantic Validation** - Field() s pattern, gt, max_length
- [ ] **L3: Service Guards** - `can_delete()` checks v service layer
- [ ] **L4: Transaction Safety** - safe_commit() pattern, no raw `db.commit()`
- [ ] **L5: Integration Tests** - cascade delete, FK constraints testované

#### 6.4 Audit Trail
- [ ] **AuditMixin** - všechny modely dědí `created_at`, `updated_at`, `created_by`, `updated_by`
- [ ] **Soft delete** - `deleted_at`, `deleted_by` přítomné
- [ ] **Version locking** - optimistic locking přes `version` column

---

### SECTION 7: Documentation 📚

#### 7.1 Code Documentation
- [ ] **Docstrings** - všechny public funkce mají docstring
- [ ] **Type hints** - všechny funkce mají type annotations
- [ ] **Inline comments** - komplexní logika má vysvětlení

#### 7.2 Project Documentation
- [ ] **CHANGELOG.md** - aktualizován s novou verzí
- [ ] **README.md** - verze číslo odpovídá `package.json` / `pyproject.toml`
- [ ] **ARCHITECTURE.md** - aktuální stack (Vue 3, FastAPI, SQLite), žádné deprecated tech (Alpine.js)

#### 7.3 ADR Documentation
- [ ] **ADR created** - nová architektonická rozhodnutí zdokumentována
- [ ] **ADR archived** - deprecated ADRs přesunuty do `docs/archive/`
- [ ] **ADR index** - `docs/ADR/README.md` obsahuje všechny aktivní ADRs

#### 7.4 Session Documentation
- [ ] **CLAUDE.local.md** - aktualizován s lessons learned
- [ ] **Session notes** - dočasné notes přesunuty do `docs/audits/` nebo smazány
- [ ] **L-040 compliance** - žádné `.md` soubory v rootu (kromě README, CHANGELOG, CLAUDE.md)

---

### SECTION 8: Dependencies 📦

#### 8.1 Security Vulnerabilities
- [ ] **npm audit** - 0 high/critical vulnerabilities
  ```bash
  cd frontend && npm audit --production
  ```
- [ ] **pip audit** - 0 high/critical (use `pip-audit` nebo `safety`)
  ```bash
  pip-audit
  ```

#### 8.2 Outdated Packages
- [ ] **Major updates** - žádné 2+ major versions zastaralé kritické dependencies
- [ ] **Security patches** - všechny security patches aplikované

#### 8.3 Unused Dependencies
- [ ] **Dead imports** - žádné nepoužívané packages v `package.json` / `requirements.txt`
  ```bash
  npm ls --all | grep "extraneous"  # npm
  pip list --not-required           # pip
  ```

#### 8.4 License Compliance
- [ ] **GPL/AGPL check** - žádné GPL/AGPL dependencies (konflikt s komerční licencí)

---

## 🚨 BLOCKING CRITERIA (P0)

**Tyto issues BLOKUJÍ git tag - MUSÍ být fixnuty:**

| # | Issue | Check |
|---|-------|-------|
| 1 | Security vulnerability (auth bypass, SQL injection) | SECTION 4 |
| 2 | Test failures (`pytest` nebo `vitest` FAIL) | SECTION 2.3 |
| 3 | Build failure (`npm run build` FAIL) | SECTION 5.3 |
| 4 | Migration failure (`alembic upgrade head` FAIL) | SECTION 6.1 |
| 5 | Missing transaction handling (raw `db.commit()` v produkci) | SECTION 1.3 L-008 |
| 6 | Missing FK ondelete → orphaned records risk | SECTION 6.2 |
| 7 | Component >300 LOC → L-036 violation | SECTION 1.3 |
| 8 | Secrets in code → L-042 violation | SECTION 1.3 |

---

## ⚠️ WARNING CRITERIA (P1)

**Měly by být fixnuty před release:**

| # | Issue | Check |
|---|-------|-------|
| 1 | Missing tests pro nové routery/services | SECTION 2.1 |
| 2 | DRY violations (duplicate CSS, logic) | SECTION 1.2 |
| 3 | Performance bottlenecks (N+1 queries) | SECTION 5.1 |
| 4 | Large files (>800 LOC Python, >300 LOC Vue) | SECTION 1.4, 5.4 |
| 5 | Missing docstrings/type hints | SECTION 7.1 |
| 6 | Outdated documentation (README, ARCHITECTURE) | SECTION 7.2 |
| 7 | Missing ADR pro nový pattern | SECTION 3.1 |

---

## 📊 SCORING SYSTEM

### Výpočet skóre

```python
total_score = (
    code_quality_score * 0.20 +
    test_coverage_score * 0.20 +
    architecture_score * 0.15 +
    security_score * 0.20 +
    performance_score * 0.10 +
    database_score * 0.10 +
    documentation_score * 0.05 +
    dependencies_score * 0.00  # informativní
) * 100
```

### Verdikt

| Score | Status | Action |
|-------|--------|--------|
| **90-100** | 🟢 **EXCELLENT** | ✅ APPROVED - immediate deploy |
| **75-89** | 🟡 **GOOD** | ⚠️ APPROVED s minor warnings |
| **60-74** | 🟠 **ACCEPTABLE** | ⚠️ Fix P1 issues před deploy |
| **<60** | 🔴 **FAILED** | ❌ BLOCKED - fix P0 issues |

---

## 🔄 AUDIT WORKFLOW

### Pre-Audit Preparation
```bash
# 1. Ensure clean working directory
git status

# 2. Run tests
pytest -v
cd frontend && npm run test

# 3. Build frontend
cd frontend && npm run build

# 4. Check migrations
alembic upgrade head
```

### Audit Execution
```bash
# Launch Auditor agent (from main chat)
# User says: "Chci hluboký audit před verzí"

# OR explicitly launch:
# Task tool with subagent_type: "auditor"
# prompt: "Proveď COMPREHENSIVE PRE-RELEASE AUDIT podle docs/core/AUDIT-FRAMEWORK.md"
```

### Post-Audit Actions

**IF APPROVED (score ≥75):**
1. Fix all P0 issues (if any)
2. Re-run audit → APPROVED
3. Update `CHANGELOG.md` s novou verzí
4. Commit audit report:
   ```bash
   git add docs/audits/2026-02-XX-pre-release-audit.md
   git commit -m "docs: pre-release audit vX.Y.Z - APPROVED"
   ```
5. Create git tag:
   ```bash
   git tag -a vX.Y.Z -m "Release vX.Y.Z - [feature summary]"
   git push origin vX.Y.Z
   ```

**IF BLOCKED (score <60):**
1. Create backlog tickets pro P0 issues
2. Fix P0 issues
3. Re-run audit
4. Iterate until APPROVED

---

## 🛠️ AUDIT TOOLS & COMMANDS

### Backend Static Analysis
```bash
# Find raw db.commit() without try/except
grep -rn "db.commit()" app/routers/ app/services/ | grep -v "try:"

# Find bare except
grep -rn "except:" app/ | grep -v "except.*:"

# Find print/breakpoint in production code
grep -rn "print(" app/services/ app/routers/ app/models/
grep -rn "breakpoint()" app/

# Find secrets patterns
grep -rEi "(api_key|password|secret|token)\s*=\s*['\"]" app/
```

### Frontend Static Analysis
```bash
# Find console.log/debugger
grep -rn "console.log" frontend/src/components/ frontend/src/stores/
grep -rn "debugger" frontend/src/

# Find hardcoded colors
grep -rEn "#[0-9a-fA-F]{3,6}" frontend/src/components/

# Find large components
find frontend/src/components -name "*.vue" -exec wc -l {} + | sort -rn | head -20

# Find TypeScript `any` type
grep -rn ": any" frontend/src/
```

### Test Coverage
```bash
# Backend test coverage (with pytest-cov)
pytest --cov=app --cov-report=term-missing

# Frontend test coverage
cd frontend && npm run test -- --coverage
```

### Database Integrity
```bash
# Check migration status
alembic current
alembic history

# Test up/down migration
alembic upgrade head
alembic downgrade -1
alembic upgrade head

# Find missing FK ondelete
grep -rn "ForeignKey(" app/models/ | grep -v "ondelete="
```

---

## 📝 AUDIT REPORT TEMPLATE

```markdown
# [AUDIT TYPE] AUDIT REPORT

**Date:** YYYY-MM-DD
**Phase:** [feature/cleanup/migration description]
**Auditor:** Claude Opus 4.5
**Duration:** ~X minutes

---

## EXECUTIVE SUMMARY

**Overall Status:** [🟢 APPROVED / 🟡 APPROVED with warnings / 🔴 BLOCKED]

| Metric | Value |
|--------|-------|
| **Total Score** | X/100 |
| **Critical Issues (P0)** | X |
| **Warnings (P1)** | X |
| **Recommendations (P2)** | X |

### Quick Score

| Section | Status | Score | Critical Issues |
|---------|--------|-------|-----------------|
| 1. Code Quality | [🟢/🟡/🔴] | X/100 | ... |
| 2. Test Coverage | [🟢/🟡/🔴] | X/100 | ... |
| 3. Architecture | [🟢/🟡/🔴] | X/100 | ... |
| 4. Security | [🟢/🟡/🔴] | X/100 | ... |
| 5. Performance | [🟢/🟡/🔴] | X/100 | ... |
| 6. Database | [🟢/🟡/🔴] | X/100 | ... |
| 7. Documentation | [🟢/🟡/🔴] | X/100 | ... |
| 8. Dependencies | [🟢/🟡/🔴] | X/100 | ... |

---

## DETAILED FINDINGS

[Per section detailed findings...]

---

## CRITICAL ISSUES (P0) - BLOCKING

[List of P0 issues with fix instructions...]

---

## WARNINGS (P1) - RECOMMENDED

[List of P1 issues...]

---

## RECOMMENDATIONS (P2)

[Nice-to-have improvements...]

---

## VERDICT

[🟢 APPROVED / 🟡 APPROVED with conditions / 🔴 BLOCKED]

**Reasoning:** [1-2 paragraphs explaining the decision]

**Next Steps:**
- [ ] Fix P0 issues
- [ ] Re-audit
- [ ] Update CHANGELOG
- [ ] Git tag vX.Y.Z

---

**Approved by:** Claude Opus 4.5
**Date:** YYYY-MM-DD HH:MM
```

---

## 🎓 LESSONS LEARNED INTEGRATION

**Po každém auditu:**
1. Nové anti-patterns → `docs/reference/ANTI-PATTERNS.md` (L-XXX)
2. Opakující se issues → Hook enforcement (přidat do `.claude/hooks/validate_*.py`)
3. Workflow gaps → Tento dokument (AUDIT-FRAMEWORK.md)
4. Session learnings → `CLAUDE.local.md` (automaticky přes Stop hook)

---

**Maintained by:** Auditor Agent
**Last Updated:** 2026-02-08
**Version:** 1.0
