# POST-PHASE AUDIT - Deep Quality Review

**Version:** 1.0
**Created:** 2026-02-01
**Purpose:** Comprehensive audit checklist pro významné fáze vývoje
**Time estimate:** 4-8 hodin (deep audit)
**Automation:** `python scripts/audit/run_full_audit.py`

---

## 📋 Kdy provést audit?

**Mandatory trigger events:**
- ✅ Před merge do main branch (major feature)
- ✅ Před release (každá verze)
- ✅ Po schema změně (alembic migration)
- ✅ Po refactoringu 5+ souborů
- ✅ Po security incident/fix
- ✅ Měsíční periodic review (first week of month)

**Výsledek:**
- 🔴 **BLOCKED** - kritické issues, nelze merge/deploy
- 🟡 **WARNINGS** - non-blocking, ale vyžaduje plán na fix
- 🟢 **APPROVED** - čisté, ready to merge/deploy

---

## ⚡ QUICK CHECKLIST (High-Level)

Projdi rychle před deep auditem - pokud některá sekce FAIL → STOP a oprav.

```
□ Všechny testy prošly (pytest + vitest)
□ Žádné TODO/FIXME v kódu (nebo jsou v tickets)
□ CHANGELOG.md aktualizován
□ Žádné console.log/print() v produkci
□ Žádné hardcoded credentials/API keys
□ Všechny nové API endpoints mají testy
□ Design system dodržen (žádné hardcoded CSS)
□ Žádné emoji v produkčním UI (L-038)
□ Git má pouze relevantní změny (ne temp files)
□ ADR vytvořen/aktualizován (pokud nový pattern)
```

**IF kterákoliv položka = ❌ → FIX FIRST před deep auditem!**

---

## 1️⃣ CODE QUALITY AUDIT (30-60 min)

### 1.1 Dead Code Detection

**Manuální:**
```bash
# Unused imports (Python)
grep -r "^import \|^from " app/ --include="*.py" | sort | uniq -c | sort -rn

# Unused functions (search for definitions never called)
# Manual review: funkce defined ale není v grep results

# Unused Vue components
grep -r "import.*from.*components" frontend/src --include="*.vue" | awk '{print $2}'
# Cross-check s usage v <template>
```

**Automatizovaně:**
```bash
python scripts/audit/audit_code_quality.py --check dead-code
```

**Kritéria:**
- ✅ **PASS:** Žádný dead code OR označený jako "intentional backup"
- 🟡 **WARN:** <5% dead code (tolerováno pro deprecated transitions)
- 🔴 **FAIL:** >5% dead code OR dead code v core modules

---

### 1.2 Duplicity (DRY Violations)

**Critical patterns k checknutí:**

```bash
# Duplicate CSS utilities (L-033, L-034)
grep -r "^\.btn\s*{" frontend/src --include="*.vue" --include="*.css" | wc -l
# MUST = 0 (jen v design-system.css)

grep -r "^\.badge" frontend/src --include="*.vue" --include="*.css" | wc -l
# MUST = 0

grep -r "font-size:\s*[0-9]" frontend/src --include="*.vue" --include="*.css" | wc -l
# MUST = 0 (jen design tokens)

# Duplicate business logic (L-001, L-002)
grep -r "calculatePrice\|calculateTime" app/ frontend/src/
# Python services/ = ✅, JS = 🔴 FAIL

# Duplicate validation logic
grep -r "Field(.*gt=0" app/models/ | sort | uniq -c | sort -rn
# Check for same validations duplicated
```

**Automatizovaně:**
```bash
python scripts/audit/audit_code_quality.py --check duplicity
```

**Kritéria:**
- ✅ **PASS:** Žádné duplicate utilities, business logic v Python
- 🔴 **FAIL:** Duplicate CSS classes, calculations in JS

---

### 1.3 Anti-Pattern Detection (L-001 až L-038)

**Blokovací patterns (CRITICAL!):**

| ID | Check | Command | Severity |
|----|-------|---------|----------|
| L-001 | Výpočty v JS | `grep -r "calculate.*=" frontend/src/` | 🔴 BLOCK |
| L-008 | Chybí try/except | `grep -L "try:" app/routers/*.py` | 🔴 BLOCK |
| L-015 | Validation walkaround | Manual review ADRs | 🔴 BLOCK |
| L-033 | Duplicate CSS | `grep "^\.btn\|^\.badge" frontend/` | 🔴 BLOCK |
| L-036 | Hardcoded CSS | `grep "font-size: [0-9]" frontend/` | 🔴 BLOCK |
| L-038 | Emoji v UI | `grep -r "[🀀-🿿😀-🙏🚀-🛿]" frontend/src` | 🔴 BLOCK |

**Warning patterns (fix recommended):**

| ID | Check | Severity |
|----|-------|----------|
| L-036 | Fat component >300 LOC | 🟡 WARN |
| L-010 | Záplatování (multiple try/fix) | 🟡 WARN |
| L-035 | Piece-by-piece cleanup | 🟡 WARN |

**Kompletní check:**
```bash
python scripts/audit/audit_code_quality.py --check anti-patterns --verbose
```

**Kritéria:**
- ✅ **PASS:** Žádné blocking anti-patterns
- 🟡 **WARN:** 1-3 warning patterns s plánem na fix
- 🔴 **FAIL:** Jakýkoliv blocking anti-pattern detected

---

### 1.4 Complexity Metrics

**Python:**
```bash
# Cyclomatic complexity (radon)
radon cc app/ -a -nb
# Target: Average A-B (simple-low), WARN: C, FAIL: D-F

# Maintainability Index
radon mi app/ -nb
# Target: A (high maintainability)

# LOC per file
find app/ -name "*.py" -exec wc -l {} + | sort -rn | head -20
# WARN: >500 LOC, FAIL: >1000 LOC
```

**Vue:**
```bash
# LOC per component
find frontend/src/components -name "*.vue" -exec wc -l {} + | sort -rn | head -20
# Target: <300 LOC (L-036), WARN: 300-500, FAIL: >500
```

**Kritéria:**
- ✅ **PASS:** Avg complexity A-B, components <300 LOC
- 🟡 **WARN:** Avg complexity C, some components 300-500 LOC
- 🔴 **FAIL:** Avg complexity D+, components >500 LOC

---

## 2️⃣ TEST COVERAGE AUDIT (30-60 min)

### 2.1 Unit Test Coverage

**Backend (pytest):**
```bash
# Run with coverage
pytest tests/ --cov=app --cov-report=term-missing --cov-report=html

# Check critical modules
pytest tests/ --cov=app/services --cov-report=term-missing
# Target: >90% for services/ (business logic)

pytest tests/ --cov=app/routers --cov-report=term-missing
# Target: >80% for routers/ (API endpoints)
```

**Frontend (vitest):**
```bash
# Run with coverage
npm run test:unit -- --coverage

# Check stores coverage
npm run test:unit -- --coverage src/stores/
# Target: >80% for Pinia stores
```

**Automatizovaně:**
```bash
python scripts/audit/audit_tests.py --coverage
```

**Kritéria:**
- ✅ **PASS:** services/ >90%, routers/ >80%, stores/ >80%
- 🟡 **WARN:** services/ 75-90%, routers/ 60-80%, stores/ 60-80%
- 🔴 **FAIL:** services/ <75%, routers/ <60%, stores/ <60%

---

### 2.2 Critical Business Logic Tests

**Must-have testy (podle TESTING.md):**

```bash
# Pricing calculations (CRITICAL!)
pytest tests/test_pricing.py -v -m critical
# MUST: 100% pass

# Time calculations
pytest tests/test_conditions.py -v -m critical
# MUST: 100% pass

# Authentication & RBAC
pytest tests/test_authentication.py -v
# MUST: 100% pass

# Backup/restore
pytest tests/test_backup.py -v
# MUST: 100% pass
```

**Chybějící critical testy:**
```bash
# Check for new API endpoints without tests
grep -r "router\.(get|post|put|delete)" app/routers/ | wc -l
pytest tests/ --collect-only | grep "test_.*router" | wc -l
# IF rozdíl > 0 → missing tests!
```

**Kritéria:**
- ✅ **PASS:** Všechny critical testy 100% pass, všechny API endpoints mají testy
- 🔴 **FAIL:** Jakýkoliv critical test fail OR nový endpoint bez testu

---

### 2.3 Edge Cases Coverage

**Checklist:**
```
□ Zero/null values tested (0, None, empty string)
□ Negative values tested (where validation should block)
□ Maximum values tested (INT_MAX, string length limits)
□ Invalid foreign keys tested (404 responses)
□ Concurrent modifications tested (optimistic locking)
□ Empty states tested (empty lists, no results)
```

**Review test files:**
```bash
# Find edge case tests
grep -r "test.*zero\|test.*null\|test.*empty\|test.*invalid" tests/
```

**Kritéria:**
- ✅ **PASS:** Všechny critical funkce mají edge case tests
- 🟡 **WARN:** 80%+ edge cases covered
- 🔴 **FAIL:** <80% edge cases OR chybí test pro known bug scenario

---

## 3️⃣ ARCHITECTURE COMPLIANCE (45-90 min)

### 3.1 ADR Adherence

**Check:**
```bash
# List all ADRs
ls docs/ADR/*.md

# Critical ADRs k ověření:
# ADR-017: 8-digit numbering (PPXXXXXX format)
# ADR-024: MaterialInput refactor (lean Part model)
# ADR-008: Optimistic locking (version field)
# ADR-012: Minimal snapshot (batch freeze)
```

**Manual review questions:**
```
□ Je nový pattern pokrytý existujícím ADR?
□ Pokud ne, byl vytvořen nový ADR?
□ Jsou všechny nové entity numbered podle ADR-017?
□ Je optimistic locking implementován na mutacích? (ADR-008)
□ Používá snapshot service správně? (ADR-012)
```

**Automatizovaně:**
```bash
# Check 8-digit numbering pattern
grep -r "id.*=.*Column.*Integer.*primary_key" app/models/ -A 2 | grep autoincrement
# Verify sequence starts comply with ADR-017
```

**Kritéria:**
- ✅ **PASS:** Všechny patterns mají ADR, nové ADRs vytvořeny kde potřeba
- 🟡 **WARN:** Minor deviace s dokumentovaným důvodem
- 🔴 **FAIL:** Nový pattern bez ADR OR violation ADR-017, ADR-008

---

### 3.2 Design System Compliance

**Critical checks:**

```bash
# 1. NO hardcoded CSS values (L-036)
grep -r "font-size:\s*[0-9]" frontend/src --include="*.vue" --include="*.css"
# MUST = 0

grep -r "padding:\s*[0-9]" frontend/src --include="*.vue" --include="*.css" | grep -v "var(--"
# MUST = 0 (unless var(--space-*))

# 2. NO duplicate utility classes (L-033, L-034)
grep -r "^\.btn\|^\.badge\|^\.card" frontend/src --include="*.vue"
# MUST = 0 (jen v design-system.css)

# 3. Lucide icons only (L-038)
grep -r "[🀀-🿿😀-🙏🚀-🛿]" frontend/src --include="*.vue" --include="*.ts" \
  --exclude-dir="__tests__"
# MUST = 0

# 4. Design tokens usage
grep -r "var(--" frontend/src --include="*.vue" --include="*.css" | wc -l
# Should be HIGH (using tokens)
```

**Design system checklist:**
```
□ Všechny komponenty používají design tokens (--text-*, --space-*, --color-*)
□ Žádné hardcoded font-size, padding, margin hodnoty
□ Žádné duplicate CSS classes v komponentách
□ Všechny ikony jsou Lucide komponenty (ne emoji)
□ Color contrast splňuje WCAG 2.1 AA (check design-system.css)
```

**Kritéria:**
- ✅ **PASS:** 100% compliance s design systemem
- 🟡 **WARN:** 1-3 minor violations (temp workarounds dokumentovány)
- 🔴 **FAIL:** Hardcoded CSS, duplicate utilities, emoji v UI

---

### 3.3 Generic-First Principle (L-036, L-039)

**Review:**
```bash
# Find large components
find frontend/src/components -name "*.vue" -exec wc -l {} + | awk '$1 > 300'

# Find duplicate patterns (kandidáti na extraction)
# Manual review: podobné komponenty s copy/paste kódem
```

**Questions:**
```
□ Jsou komponenty <300 LOC?
□ Jsou komponenty reusable (ne context-specific)?
□ Jsou composables použity pro sdílenou logiku?
□ Je stejná logika duplikována nebo extractovaná?
□ Nové komponenty následují building blocks pattern?
```

**Kritéria:**
- ✅ **PASS:** Komponenty <300 LOC, reusable patterns
- 🟡 **WARN:** 1-2 komponenty 300-500 LOC s plánem na refactor
- 🔴 **FAIL:** Komponenty >500 LOC OR massive duplicity

---

## 4️⃣ SECURITY AUDIT (60-120 min)

### 4.1 OWASP Top 10 Review

**A01: Broken Access Control**
```bash
# Check all API endpoints have auth checks
grep -r "@router\.(get|post|put|delete)" app/routers/ -A 10 | grep -E "current_user|require_auth"
# Every endpoint MUST have auth check OR explicitly public

# Check RBAC enforcement
grep -r "role.*==.*Role\." app/routers/
# Verify role checks where needed
```

**A02: Cryptographic Failures**
```bash
# NO hardcoded secrets
grep -ri "password.*=.*['\"]" app/ config/ --include="*.py"
grep -ri "api_key.*=.*['\"]" app/ config/ --include="*.py"
grep -ri "secret.*=.*['\"]" app/ config/ --include="*.py"
# MUST = 0 (use .env)

# Check .env.example exists
ls .env.example
# MUST exist with placeholder values
```

**A03: Injection (SQL, XSS)**
```bash
# NO raw SQL queries (use ORM)
grep -r "execute.*SELECT\|execute.*INSERT\|execute.*UPDATE" app/ --include="*.py"
# WARN if found (review for parameterization)

# NO v-html with user input
grep -r "v-html" frontend/src --include="*.vue"
# Review each usage - user input MUST be sanitized

# Pydantic validation on all inputs
grep -r "class.*BaseModel" app/ -A 20 | grep "Field("
# Every input field SHOULD have validation
```

**A04: Insecure Design**
```bash
# Review authentication flow
cat app/routers/auth_router.py
# Check: password hashing, JWT expiry, HttpOnly cookies

# Check rate limiting
grep -r "rate_limit" app/
# Verify endpoints are rate-limited
```

**A05: Security Misconfiguration**
```bash
# CSP headers configured (ADR-020)
grep -r "Content-Security-Policy" app/gestima_app.py
# MUST exist

# HSTS headers
grep -r "Strict-Transport-Security" app/gestima_app.py
# MUST exist

# Debug mode OFF in production
grep -r "debug.*=.*True" app/ config/
# MUST = 0 in production config
```

**A06-A10:** (Abbreviated)
- **A06 Vulnerable Components:** Check dependencies (section 4.2)
- **A07 Auth Failures:** JWT + HttpOnly cookies ✅ (ADR-005)
- **A08 Software Integrity:** (not applicable - no CDN)
- **A09 Logging Failures:** Check logging (section 4.3)
- **A10 SSRF:** (low risk - no user-provided URLs)

**Automatizovaně:**
```bash
python scripts/audit/audit_security.py --owasp
```

---

### 4.2 Dependency Vulnerabilities

**Backend:**
```bash
# Check for known vulnerabilities (safety)
pip install safety
safety check --json
# Review all CRITICAL and HIGH severity

# Check outdated packages
pip list --outdated
```

**Frontend:**
```bash
# npm audit
npm audit --audit-level=moderate
# Fix all CRITICAL and HIGH

# Check outdated
npm outdated
```

**Automatizovaně:**
```bash
python scripts/audit/audit_dependencies.py --vulnerabilities
```

**Kritéria:**
- ✅ **PASS:** Zero CRITICAL, zero HIGH vulnerabilities
- 🟡 **WARN:** 1-3 MODERATE vulnerabilities with mitigation plan
- 🔴 **FAIL:** ANY CRITICAL or >5 HIGH vulnerabilities

---

### 4.3 Input Validation (L-009)

**Check all Pydantic models:**
```bash
# Find models without Field() validations
grep -r "class.*BaseModel" app/ -A 30 | grep -B 30 "^\s*\w\+:\s*\(int\|str\|float\)" | grep -v "Field("
# Review: should have Field(gt=0, max_length, etc.)
```

**Critical validations:**
```python
# Positive numbers
Field(..., gt=0)  # prices, quantities

# Non-negative
Field(..., ge=0)  # indices, counts

# String lengths
Field(..., max_length=200)  # prevent DoS

# Enums
Field(..., pattern="^(draft|active|archived)$")  # status
```

**Kritéria:**
- ✅ **PASS:** Všechny user inputs mají Pydantic validation
- 🟡 **WARN:** 90%+ covered, minor gaps
- 🔴 **FAIL:** <90% coverage OR missing validation na critical endpoint

---

### 4.4 Authentication & Authorization

**Checklist:**
```
□ JWT tokens expire (check settings)
□ HttpOnly cookies used (ADR-005)
□ Passwords hashed (bcrypt/argon2)
□ Role hierarchy enforced (Admin >= Operator >= Viewer)
□ Protected endpoints require auth
□ RBAC checked on mutations (POST/PUT/DELETE)
□ No credentials in git history (git log --all | grep -i password)
```

**Test:**
```bash
# Try accessing protected endpoint without token
curl http://localhost:8001/api/parts
# Should return 401 Unauthorized
```

**Kritéria:**
- ✅ **PASS:** All checks ✅
- 🔴 **FAIL:** Any auth/authz gap

---

## 5️⃣ PERFORMANCE AUDIT (30-60 min)

### 5.1 N+1 Query Detection

**Manual review:**
```bash
# Find ORM queries in loops
grep -r "for.*in.*:" app/routers/ -A 10 | grep "session\.(query|execute)"
# Review each: likely N+1 if querying inside loop

# Check for lazy loading
grep -r "lazy.*=" app/models/ --include="*.py"
# Should be minimal (use joinedload/selectinload)
```

**Enable SQL logging (temporary):**
```python
# app/database.py
engine = create_async_engine(
    DATABASE_URL,
    echo=True  # <-- temporary for debugging
)
```

**Load test critical endpoints:**
```bash
# Example: list parts (should be <100ms)
time curl http://localhost:8001/api/parts
```

**Automatizovaně:**
```bash
python scripts/audit/audit_performance.py --n-plus-one
```

**Kritéria:**
- ✅ **PASS:** No N+1 queries in critical paths
- 🟡 **WARN:** N+1 in non-critical low-traffic endpoints
- 🔴 **FAIL:** N+1 in list/search endpoints

---

### 5.2 API Response Times

**Target thresholds:**
- List endpoints: <100ms
- Detail endpoints: <50ms
- Mutations: <200ms
- Reports/exports: <2s

**Test:**
```bash
# Use httpie with timing
pip install httpie

# List parts
http GET :8001/api/parts --print=hH --timeout=5
# Check X-Process-Time header OR use time command

# Detail
http GET :8001/api/parts/10000001 --print=hH
```

**Load testing (optional):**
```bash
# Install ab (Apache Bench)
ab -n 100 -c 10 http://localhost:8001/api/parts
# Check: mean response time, 95th percentile
```

**Kritéria:**
- ✅ **PASS:** All endpoints within thresholds
- 🟡 **WARN:** 1-2 endpoints slightly over (plan optimization)
- 🔴 **FAIL:** Critical endpoint >2x threshold

---

### 5.3 Frontend Bundle Size

**Check:**
```bash
# Build production
npm run build

# Analyze bundle
du -sh frontend/dist/assets/*.js | sort -h
# Target: main bundle <500KB, vendor <1MB

# Check for large dependencies
npm list --depth=0 --long
```

**Kritéria:**
- ✅ **PASS:** Main <500KB, vendor <1MB
- 🟡 **WARN:** Main 500-800KB, vendor 1-1.5MB
- 🔴 **FAIL:** Main >800KB OR vendor >1.5MB

---

### 5.4 Database Indexes

**Review models:**
```bash
# Find columns queried frequently but not indexed
grep -r "filter.*==" app/routers/ -o | sort | uniq -c | sort -rn
# Cross-check with model definitions for index=True
```

**Check existing indexes:**
```bash
# SQLite
sqlite3 data/gestima.db ".indexes"
sqlite3 data/gestima.db ".schema parts" | grep INDEX
```

**Kritéria:**
- ✅ **PASS:** All frequently queried columns indexed
- 🟡 **WARN:** 1-2 missing indexes on low-traffic tables
- 🔴 **FAIL:** Missing index on critical query (parts, operations)

---

## 6️⃣ DATABASE AUDIT (30-45 min)

### 6.1 Migration Integrity

**Check:**
```bash
# List migrations
ls alembic/versions/*.py | wc -l

# Check for migration conflicts (duplicate revision IDs)
grep -r "^revision = " alembic/versions/ | sort | uniq -c | sort -rn
# MUST: každý revision jedinečný

# Check down_revision chain
grep -r "^down_revision = " alembic/versions/
# SHOULD: form linear chain (no branches unless intentional)
```

**Test migration up/down:**
```bash
# Backup first!
cp data/gestima.db data/gestima.db.backup

# Downgrade 1 version
alembic downgrade -1

# Upgrade back
alembic upgrade head

# Verify data integrity
sqlite3 data/gestima.db "SELECT COUNT(*) FROM parts"
```

**Automatizovaně:**
```bash
python scripts/audit/audit_database.py --migrations
```

**Kritéria:**
- ✅ **PASS:** All migrations apply cleanly up/down
- 🟡 **WARN:** 1 migration has minor issue (documented)
- 🔴 **FAIL:** Migration fails OR data loss on down/up

---

### 6.2 Constraints & Referential Integrity

**Check:**
```bash
# Foreign key constraints
sqlite3 data/gestima.db "PRAGMA foreign_key_list(parts)"
sqlite3 data/gestima.db "PRAGMA foreign_key_list(operations)"
sqlite3 data/gestima.db "PRAGMA foreign_key_list(batches)"

# Verify ON DELETE behavior
grep -r "ondelete=" app/models/ --include="*.py"
# Check: CASCADE vs RESTRICT (per ADR decisions)

# Unique constraints
sqlite3 data/gestima.db ".schema" | grep UNIQUE
```

**Test referential integrity:**
```bash
# Try to delete parent with children (should fail if RESTRICT)
# Manual test via API or SQL
```

**Kritéria:**
- ✅ **PASS:** All FK constraints correct, orphaned data = 0
- 🟡 **WARN:** 1-2 orphaned records (old data cleanup needed)
- 🔴 **FAIL:** Missing FK constraint OR cascade incorrect

---

### 6.3 Data Consistency

**Check for orphaned records:**
```bash
# Operations without parts
sqlite3 data/gestima.db "
SELECT COUNT(*) FROM operations o
LEFT JOIN parts p ON o.part_id = p.id
WHERE p.id IS NULL
"
# MUST = 0

# Batches without parts
sqlite3 data/gestima.db "
SELECT COUNT(*) FROM batches b
LEFT JOIN parts p ON b.part_id = p.id
WHERE p.id IS NULL
"
# MUST = 0
```

**Check audit fields:**
```bash
# Rows without created_by (L-007)
sqlite3 data/gestima.db "
SELECT COUNT(*) FROM parts WHERE created_by IS NULL
"
# SHOULD = 0 (unless old migrated data)
```

**Automatizovaně:**
```bash
python scripts/audit/audit_database.py --consistency
```

**Kritéria:**
- ✅ **PASS:** Zero orphaned records, audit fields populated
- 🟡 **WARN:** <1% orphaned (old migrated data)
- 🔴 **FAIL:** >1% orphaned OR missing audit fields on new records

---

### 6.4 Backup Verification

**Check backup strategy:**
```bash
# List recent backups
ls -lh backups/*.db | tail -5

# Test restore
python gestima.py restore-backup backups/latest.db --test
# Verify: data intact, counts match
```

**Backup checklist:**
```
□ Automated daily backups configured?
□ Backup rotation working (cleanup old)?
□ Backup tested successfully within last 30 days?
□ Backup stored off-site (or different disk)?
□ Recovery procedure documented?
```

**Kritéria:**
- ✅ **PASS:** All checks ✅, recent test restore successful
- 🟡 **WARN:** Backups exist but test restore >30 days ago
- 🔴 **FAIL:** No backups OR restore fails

---

## 7️⃣ DOCUMENTATION AUDIT (15-30 min)

### 7.1 CHANGELOG.md

**Check:**
```bash
# Last entry date
head -20 CHANGELOG.md | grep "##"
# SHOULD match recent work

# Version tags
git tag -l
# SHOULD match CHANGELOG versions
```

**Checklist:**
```
□ Poslední změny v CHANGELOG.md?
□ Formát: ## [Version] - YYYY-MM-DD?
□ Sekce: Added, Changed, Fixed, Removed?
□ Breaking changes označeny?
```

**Kritéria:**
- ✅ **PASS:** CHANGELOG aktuální, complete
- 🟡 **WARN:** Minor gaps (can be fixed quickly)
- 🔴 **FAIL:** CHANGELOG >2 weeks out of date

---

### 7.2 ADR Documentation

**Review:**
```bash
# Count ADRs
ls docs/ADR/*.md | wc -l

# Check for new patterns without ADR
# Manual review: new architectural decisions made?
```

**Questions:**
```
□ Nový pattern má ADR?
□ Deprecated pattern má ADR-XXX-superseded?
□ ADR obsahuje: Context, Decision, Consequences?
□ ADR je linkován z relevantních souborů?
```

**Kritéria:**
- ✅ **PASS:** All patterns documented, ADRs complete
- 🟡 **WARN:** Minor ADR update needed (not blocking)
- 🔴 **FAIL:** Major pattern without ADR

---

### 7.3 Inline Code Comments

**Review:**
```bash
# Find complex functions without docstrings
grep -r "^def \|^async def " app/ --include="*.py" -A 5 | grep -B 5 -v '"""'
# Review: complex logic SHOULD have docstring

# Find TODOs
grep -r "TODO\|FIXME\|XXX" app/ frontend/src/ --exclude-dir=node_modules
# Each TODO SHOULD have ticket/issue OR plan
```

**Kritéria:**
- ✅ **PASS:** Complex functions documented, TODOs tracked
- 🟡 **WARN:** Few undocumented functions (plan to fix)
- 🔴 **FAIL:** Many undocumented critical functions

---

### 7.4 API Documentation (OpenAPI)

**Check:**
```bash
# FastAPI auto-generates OpenAPI
curl http://localhost:8001/openapi.json | jq '.paths | keys'

# Verify all endpoints documented
# Should match: grep -r "@router" app/routers/
```

**Checklist:**
```
□ Všechny endpoints v OpenAPI?
□ Request/response schemas správné?
□ Descriptions vyplněny (docstrings)?
□ Examples provided pro complex requests?
```

**Kritéria:**
- ✅ **PASS:** OpenAPI complete, schemas correct
- 🟡 **WARN:** Minor gaps (descriptions)
- 🔴 **FAIL:** Missing endpoints OR wrong schemas

---

## 8️⃣ DEPENDENCIES AUDIT (15-30 min)

### 8.1 Security Vulnerabilities

**(See Section 4.2 - duplicate check)**

```bash
# Backend
safety check --json

# Frontend
npm audit --audit-level=moderate
```

**Kritéria:**
- ✅ **PASS:** Zero CRITICAL, zero HIGH
- 🟡 **WARN:** 1-3 MODERATE
- 🔴 **FAIL:** ANY CRITICAL or >5 HIGH

---

### 8.2 Outdated Dependencies

**Check:**
```bash
# Backend
pip list --outdated --format=columns

# Frontend
npm outdated
```

**Review policy:**
- **Patch updates (X.Y.Z → X.Y.Z+1):** Update immediately
- **Minor updates (X.Y → X.Y+1):** Review changelog, update if safe
- **Major updates (X → X+1):** Plan migration, test thoroughly

**Kritéria:**
- ✅ **PASS:** All patch updates applied, plan for minor/major
- 🟡 **WARN:** 1-5 outdated packages (plan exists)
- 🔴 **FAIL:** >10 outdated OR critical package >6 months old

---

### 8.3 Unused Dependencies

**Check:**
```bash
# Backend (pip)
# Manual review: compare requirements.txt vs imports
grep -r "^import \|^from " app/ | awk '{print $2}' | cut -d'.' -f1 | sort | uniq
# Cross-check with: pip list

# Frontend (npm)
npx depcheck
# Lists unused dependencies
```

**Kritéria:**
- ✅ **PASS:** Zero unused dependencies
- 🟡 **WARN:** 1-3 unused (can be removed)
- 🔴 **FAIL:** >5 unused OR bloat >50MB

---

### 8.4 License Compliance

**Check licenses:**
```bash
# Backend
pip-licenses --format=table

# Frontend
npx license-checker --summary
```

**Watch for:**
- ❌ **GPL/AGPL** - copyleft (requires source disclosure)
- ⚠️ **Custom licenses** - review terms
- ✅ **MIT/Apache/BSD** - permissive (OK)

**Kritéria:**
- ✅ **PASS:** All licenses compatible (MIT/Apache/BSD)
- 🟡 **WARN:** 1-2 weak copyleft (LGPL)
- 🔴 **FAIL:** GPL/AGPL OR unknown license

---

## 📊 AUDIT REPORT TEMPLATE

Po dokončení auditu vyplň:

```markdown
# POST-PHASE AUDIT REPORT

**Date:** YYYY-MM-DD
**Phase:** [Feature name / Release version]
**Auditor:** [Name / Team]
**Duration:** [Hours spent]

---

## EXECUTIVE SUMMARY

**Overall Status:** 🟢 APPROVED / 🟡 APPROVED WITH WARNINGS / 🔴 BLOCKED

**Critical Issues:** [count]
**Warnings:** [count]
**Passed Checks:** [count]

---

## AUDIT RESULTS

### 1️⃣ Code Quality
- Dead Code: ✅ / 🟡 / 🔴
- Duplicity: ✅ / 🟡 / 🔴
- Anti-Patterns: ✅ / 🟡 / 🔴
- Complexity: ✅ / 🟡 / 🔴

**Issues:**
- [List any issues found]

---

### 2️⃣ Test Coverage
- Unit Tests: XX% backend, XX% frontend
- Critical Tests: ✅ / 🔴
- Edge Cases: ✅ / 🟡 / 🔴

**Missing Tests:**
- [List gaps]

---

### 3️⃣ Architecture Compliance
- ADR Adherence: ✅ / 🟡 / 🔴
- Design System: ✅ / 🟡 / 🔴
- Generic-First: ✅ / 🟡 / 🔴

**Violations:**
- [List any]

---

### 4️⃣ Security
- OWASP Top 10: ✅ / 🟡 / 🔴
- Dependencies: ✅ / 🟡 / 🔴
- Input Validation: ✅ / 🟡 / 🔴
- Auth/AuthZ: ✅ / 🔴

**Vulnerabilities:**
- [List any]

---

### 5️⃣ Performance
- N+1 Queries: ✅ / 🟡 / 🔴
- API Response: ✅ / 🟡 / 🔴
- Bundle Size: ✅ / 🟡 / 🔴
- DB Indexes: ✅ / 🟡 / 🔴

**Bottlenecks:**
- [List any]

---

### 6️⃣ Database
- Migrations: ✅ / 🟡 / 🔴
- Constraints: ✅ / 🟡 / 🔴
- Consistency: ✅ / 🟡 / 🔴
- Backup: ✅ / 🟡 / 🔴

**Issues:**
- [List any]

---

### 7️⃣ Documentation
- CHANGELOG: ✅ / 🟡 / 🔴
- ADRs: ✅ / 🟡 / 🔴
- Code Comments: ✅ / 🟡 / 🔴
- API Docs: ✅ / 🟡 / 🔴

**Gaps:**
- [List any]

---

### 8️⃣ Dependencies
- Vulnerabilities: ✅ / 🟡 / 🔴
- Outdated: ✅ / 🟡 / 🔴
- Unused: ✅ / 🟡 / 🔴
- Licenses: ✅ / 🟡 / 🔴

**Actions:**
- [List updates needed]

---

## CRITICAL ISSUES (BLOCKING)

[List all 🔴 issues that MUST be fixed before merge/deploy]

1. ...
2. ...

---

## WARNINGS (RECOMMENDED)

[List all 🟡 issues that SHOULD be fixed soon]

1. ...
2. ...

---

## RECOMMENDATIONS

[Suggestions for future improvements]

1. ...
2. ...

---

## NEXT STEPS

- [ ] Fix all critical issues
- [ ] Create tickets for warnings
- [ ] Update documentation
- [ ] Re-run automated audit
- [ ] Sign-off approval

---

**Approved by:** [Name]
**Date:** YYYY-MM-DD
```

---

## 🤖 AUTOMATED AUDIT

Pro rychlejší audit použij master skript:

```bash
# Full audit (všechny sekce)
python scripts/audit/run_full_audit.py --output report.md

# Jen kritické checks
python scripts/audit/run_full_audit.py --critical-only

# Konkrétní sekce
python scripts/audit/run_full_audit.py --sections code-quality,security,tests
```

**Output:** Vygeneruje report ve formátu výše + HTML verzi.

---

## 📚 REFERENCE

| Topic | Link |
|-------|------|
| Anti-patterns | [ANTI-PATTERNS.md](../reference/ANTI-PATTERNS.md) |
| Blocking rules | [RULES.md](../core/RULES.md) |
| ADRs | [ADR/](../ADR/) |
| Testing guide | [TESTING.md](TESTING.md) |
| Architecture | [ARCHITECTURE.md](../reference/ARCHITECTURE.md) |

---

**Version:** 1.0
**Maintainer:** Claude + Team
**Last Updated:** 2026-02-01
