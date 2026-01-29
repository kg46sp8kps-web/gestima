# BACKEND CLEANUP GUIDE - ULTIMATE EDITION

**Version:** 2.0 - ULTIMATE (všechny audity sloučeny)
**Date:** 2026-01-29
**Author:** Roy (AI Dev Team)
**Purpose:** Achieve 100% clean slate backend after Vue SPA integration

---

## Executive Summary

**Current State:**
- ✅ Backend: 10,565 LOC Python, 94% test coverage, production-ready
- ✅ Vue Phase 1 COMPLETE: Auth + Parts list working
- ✅ Sprint 1 DONE: N+1 queries, indexes, safe_commit, console.log fixed
- ✅ Sprint 2 DONE: Alembic migrations, CSP/HSTS headers
- ⚠️ Cleanup needed: 4 long functions, 10 debug prints, 2 architectural debt items

**What's Fixed from 2026-01-28 Deep Audit:**
- ✅ C-4: N+1 queries (Sprint 1: `f208ef1`)
- ✅ C-3: deleted_at indexes (Sprint 1: 12 tables)
- ✅ H-9: safe_commit() duplicates (Sprint 1: mass replace)
- ✅ H-7: Console.log cleanup (Sprint 1: 45→0)
- ✅ C-5/C-6: Migration error handling (Sprint 2: `c9c77fc`)
- ✅ H-3/H-4: CSP/HSTS headers (Sprint 2: implemented)

**What Remains:**
- ❌ C-1: SQLite FK constraints = NO ACTION (long-term)
- ❌ C-2: Float → Decimal migration (long-term)
- ❌ H-6: Frontend memory leaks (solved by Vue migration)
- ❌ H-8: Repository pattern (optional architectural improvement)
- ❌ NEW: 4 long functions (>80 LOC)
- ❌ NEW: 10 debug print() statements

**Goal:**
- 🎯 Zero technical debt
- 🎯 Zero debug prints in production
- 🎯 Thin routers (<50 LOC/function)
- 🎯 95%+ test coverage
- 🎯 100% clean slate for v2.0

**Timeline:** 3 weeks parallel with Vue Phase 2-4 migration

---

## Table of Contents

1. [Remaining Audit Issues](#1-remaining-audit-issues)
2. [New Findings (2026-01-29)](#2-new-findings-2026-01-29)
3. [Cleanup Tasks (Prioritized)](#3-cleanup-tasks-prioritized)
4. [Long-Term Migrations (v1.9.0+)](#4-long-term-migrations-v190)
5. [Post-Vue Integration Cleanup](#5-post-vue-integration-cleanup)
6. [Clean Slate Criteria](#6-clean-slate-criteria)
7. [Validation Checklist](#7-validation-checklist)
8. [Timeline Summary](#8-timeline-summary)
9. [Rollback Plan](#9-rollback-plan)
10. [Success Criteria](#10-success-criteria-final)
11. [Reference Files](#11-reference-files)
12. [Quick Start Guide](#12-quick-start-guide) ⚡

---

## 1. Remaining Audit Issues

**Source:** [docs/audits/2026-01-28-deep-audit.md](audits/2026-01-28-deep-audit.md)

### 1.1 Already Fixed (Sprint 1-2)

| Issue | Status | Fixed In |
|-------|--------|----------|
| C-4: N+1 queries | ✅ FIXED | Sprint 1 (f208ef1) |
| C-3: deleted_at indexes | ✅ FIXED | Sprint 1 (12 tables) |
| H-9: safe_commit() duplicates | ✅ FIXED | Sprint 1 (37→1) |
| H-7: Console.log (45×) | ✅ FIXED | Sprint 1 (cleanup) |
| C-5: Migration error handling | ✅ FIXED | Sprint 2 (c9c77fc) |
| C-6: Seed data error handling | ✅ FIXED | Sprint 2 (structured logging) |
| H-3: CSP headers | ✅ FIXED | Sprint 2 (Alpine.js compat) |
| H-4: HSTS headers | ✅ FIXED | Sprint 2 (HTTPS conditional) |

**Impact:** Parts list: 1200ms → 150ms, Queries: 50-200 → 3-10

---

### 1.2 Remaining from Audit (Long-Term)

#### 🔴 C-1: SQLite FK Constraints = NO ACTION (CRITICAL)

**Problem:**
```python
# Models define:
material_item_id: Mapped[int] = mapped_column(
    ForeignKey("material_items.id", ondelete="CASCADE")
)

# But SQLite has:
PRAGMA foreign_key_list(parts);
# on_delete: NO ACTION
```

**Impact:** Deleting MaterialItem doesn't cascade to Parts (orphan FKs)

**Root Cause:** SQLite doesn't support ALTER TABLE for FK changes

**Solution (Long-Term Migration):**
```python
# Alembic migration
def upgrade():
    # 1. Create new table with correct FK
    op.create_table('parts_new', ...)

    # 2. Copy data
    op.execute('INSERT INTO parts_new SELECT * FROM parts')

    # 3. Drop old, rename new
    op.drop_table('parts')
    op.rename_table('parts_new', 'parts')
```

**Affected Tables:** 12 tables with FK constraints

**Priority:** MEDIUM (workaround: manual CASCADE in Python)

**Timeline:** After v2.0 (requires downtime)

---

#### 🔴 C-2: Float → Decimal Migration (CRITICAL for Finance)

**Problem:**
```python
# Current:
unit_cost: Mapped[float] = mapped_column(Float)

# Issue:
0.1 + 0.2 = 0.30000000000000004  # ❌ Rounding errors
```

**Impact:** Financial calculations can accumulate errors

**Solution:**
```python
# Target:
unit_cost: Mapped[Decimal] = mapped_column(Numeric(10, 2))

# Alembic migration:
def upgrade():
    with op.batch_alter_table('batches') as batch_op:
        batch_op.alter_column('unit_cost',
            existing_type=sa.Float(),
            type_=sa.Numeric(10, 2),
            existing_nullable=False
        )
```

**Affected Columns:**
- `batches`: unit_cost, total_cost, material_cost, machining_cost, setup_cost, overhead_cost, margin_cost, coop_cost
- `parts`: stock_price, stock_price_per_kg
- `material_items`: price_per_kg, price_per_m, price_per_m2
- `price_categories`: overhead_percentage, margin_percentage

**Total:** ~30 columns across 5 tables

**Priority:** HIGH (but non-breaking if careful)

**Timeline:** v1.9.0 (after Vue complete, before Orders module)

---

#### 🟡 H-6: Frontend Memory Leaks (addEventListener)

**Problem:**
```javascript
// Alpine.js modules add listeners but don't remove
document.addEventListener('part-selected', handler);
// No cleanup on module destroy
```

**Impact:** Memory grows over time (SPA navigation)

**Solution:** Vue migration (auto cleanup)

**Status:** ✅ Will be solved by Vue SPA (auto unmount)

**Timeline:** Solved in Vue Phase 4 (Week 3)

---

#### 🟡 H-8: Repository Pattern Missing (OPTIONAL)

**Problem:** Data access logic scattered in routers

**Current:**
```python
# Router has DB logic:
result = await db.execute(
    select(Part).where(Part.id == id).options(selectinload(Part.operations))
)
```

**Better (Repository Pattern):**
```python
# Repository handles DB:
class PartRepository:
    async def get_with_operations(self, part_id: int) -> Part:
        return await self.db.execute(...)

# Router uses repository:
part = await part_repo.get_with_operations(part_id)
```

**Pros:**
- Cleaner separation
- Easier testing (mock repository)
- Reusable queries

**Cons:**
- Extra abstraction layer
- More boilerplate
- Current approach works fine for GESTIMA size

**Decision:** SKIP (overkill for current size, consider for v3.0+)

**Priority:** LOW (architectural preference, not necessity)

---

## 2. New Findings (2026-01-29)

**Source:** Code scan (2026-01-29)

### 2.1 Current Metrics (Post-Sprint 1-2)

| Metric | Value | Target |
|--------|-------|--------|
| Total LOC Python | 10,565 | <10,000 (-5%) |
| Test Coverage | 94% | 95%+ |
| Longest Function | 108 LOC | <50 LOC |
| Debug Print Statements | 10 | 0 |
| TODO/HACK/FIXME | 0 | 0 ✅ |
| Dead Code Files | 0 | 0 ✅ |
| Alpine.js LOC | 4,133 | 0 (Vue) |

### 1.2 Problems Identified

#### 🔴 HIGH Priority

**1. Long Functions (4 functions >80 LOC)**

```
app/routers/pricing_router.py:
├─ Line 602: freeze_loose_batches_as_set() - 99 LOC
├─ Line 421: clone_batch_set() - 84 LOC
└─ Line 275: freeze_batch_set() - 81 LOC

app/routers/parts_router.py:
└─ Line 350: copy_material_geometry() - 108 LOC
```

**Problem:** Business logic in routers, hard to test, violates SRP.

**Impact:** Medium (works but unmaintainable)

---

**2. Debug Print Statements (10x production code)**

```python
# app/services/material_parser.py
print(f"🔍 _extract_material: potential codes found: {potential_codes}")
print(f"🔍 _extract_length: original='{text}', cleaned='{cleaned_text}'")
print(f"🔍 _extract_diameter: pattern match groups: {match.groups()}")
# ... + 7 more
```

**Problem:** Debug output in production, not structured logging.

**Impact:** Low (cosmetic but unprofessional)

---

#### 🟡 MEDIUM Priority

**3. Large Router Files**

```
pricing_router.py:  25KB (700 LOC)
parts_router.py:    22KB (543 LOC)
materials_router.py: 21KB
admin_router.py:    21KB
```

**Problem:** After extracting long functions, files still large.

**Impact:** Low (Python handles this fine, but less readable)

---

**4. Alpine.js Frontend (4,133 LOC)**

```
app/static/js/modules/batch-sets.js:      701 LOC
app/static/js/core/workspace-controller.js: 753 LOC
app/static/js/modules/part-material.js:    497 LOC
app/static/js/modules/part-operations.js:  462 LOC
app/static/js/modules/part-pricing.js:     460 LOC
app/static/js/modules/parts-list.js:       268 LOC
```

**Problem:** Will become obsolete after Vue migration.

**Impact:** None (delete after Vue complete)

---

#### 🟢 LOW Priority

**5. Minor Code Smells**

- `app/services/material_parser.py`: 1 unused import (`noqa` comment)
- Some routers: Duplicated dependency patterns (normal for FastAPI)
- No major duplicate code blocks (good!)

**Problem:** Cosmetic issues only.

**Impact:** Negligible

---

## 3. Cleanup Tasks (Prioritized)

### 3.1 Phase 1: Quick Wins (1 day) 🚀

#### Task 1.1: Replace Debug Prints with Structured Logging

**File:** `app/services/material_parser.py`

**Current (10x print statements):**
```python
print(f"🔍 _extract_material: potential codes found: {potential_codes}")
print(f"🔍 _extract_length: original='{text}', cleaned='{cleaned_text}'")
```

**Fixed:**
```python
import logging
logger = logging.getLogger(__name__)

logger.debug("_extract_material: potential codes found", extra={"codes": potential_codes})
logger.debug("_extract_length: processing", extra={"original": text, "cleaned": cleaned_text})
```

**Steps:**
1. Add `import logging` + `logger = logging.getLogger(__name__)` at top
2. Replace all 10x `print(f"🔍 ...)` with `logger.debug(...)`
3. Use `extra={}` dict for structured data (not f-strings)
4. Test material parser API endpoint
5. Verify logs appear in structured format

**Validation:**
```bash
# No print statements
grep -n "print(f" app/services/material_parser.py
# Should return: (empty)

# Has logger.debug
grep -n "logger.debug" app/services/material_parser.py
# Should return: 10 lines
```

**Time:** 30 minutes

**Risk:** VERY LOW (logging only, no logic change)

---

#### Task 1.2: Remove Unused Import

**File:** `app/services/material_parser.py`

**Current:**
```python
from typing import Optional, Dict, Any, List  # noqa: F401 - some unused
```

**Fixed:**
```python
from typing import Optional, Dict, List
```

**Steps:**
1. Check which types are actually used
2. Remove unused imports
3. Remove `# noqa` comment

**Validation:**
```bash
# Run linter
pylint app/services/material_parser.py
# Should pass without noqa
```

**Time:** 5 minutes

**Risk:** NONE

---

### 3.2 Phase 2: Service Layer Refactoring (1 week)

**Follow the detailed plan from Task agent (see section 7 for full plan)**

#### Task 2.1: Extract `copy_material_geometry()` → `part_service.py`

**Priority:** HIGH
**Complexity:** LOW
**Time:** 1 day

**Steps:**
1. Create `app/services/part_service.py`
2. Extract business logic:
```python
async def copy_material_geometry_from_item(
    part: Part,
    db: AsyncSession
) -> Part:
    """Copy dimensions from MaterialItem to Part.stock_*"""
    if not part.material_item:
        raise ValueError("Part has no material assigned")

    mi = part.material_item
    part.stock_diameter = mi.diameter
    part.stock_width = mi.width
    part.stock_height = mi.thickness
    part.stock_wall_thickness = mi.wall_thickness

    logger.info(
        "Copied material geometry",
        extra={"part_id": part.id, "material_item_id": mi.id}
    )
    return part
```

3. Refactor router (parts_router.py:350):
```python
@router.post("/{part_number}/copy-material-geometry")
async def copy_material_geometry(
    part_number: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.OPERATOR]))
):
    """Copy dimensions from MaterialItem to Part.stock_*"""
    result = await db.execute(
        select(Part)
        .options(joinedload(Part.material_item))
        .where(Part.part_number == part_number)
    )
    part = result.scalar_one_or_none()
    if not part:
        raise HTTPException(status_code=404, detail="Díl nenalezen")

    try:
        await copy_material_geometry_from_item(part, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    set_audit(part, current_user.username, is_update=True)
    part = await safe_commit(db, part, "kopírování geometrie")

    return {"message": "Geometrie zkopírována", "version": part.version}
```

4. Create tests: `tests/test_part_service.py`
```python
@pytest.mark.asyncio
async def test_copy_material_geometry_success(db_session):
    """Test copying geometry from material_item"""
    # Setup: Create material_item with dimensions
    # Act: copy_material_geometry_from_item(part, db)
    # Assert: part.stock_* fields updated
    pass

@pytest.mark.asyncio
async def test_no_material_raises(db_session):
    """Test error when part has no material_item"""
    # Act + Assert: raises ValueError
    pass
```

**Validation:**
```bash
# Router function reduced
wc -l app/routers/parts_router.py
# Should show ~520 LOC (down from 543)

# Tests pass
pytest tests/test_part_service.py -v
# 2 tests passing

# Coverage maintained
pytest --cov=app --cov-report=term-missing
# Should show 94%+
```

**Outcome:**
- Router: 108 LOC → 20 LOC (-82%)
- Service: NEW (testable!)
- Test coverage: maintained

---

#### Task 2.2: Extract `freeze_batch_set()` → `batch_set_service.py`

**Priority:** HIGH
**Complexity:** MEDIUM
**Time:** 2 days

**Steps:**
1. Create `app/services/batch_set_service.py`
2. Extract freeze logic (see full service code in agent plan)
3. Refactor router endpoint
4. Create service tests (5 tests)
5. Integration tests

**Validation:**
```bash
# Service created
test -f app/services/batch_set_service.py && echo "✅ Service exists"

# Tests pass
pytest tests/test_batch_set_service.py::TestFreezeBatchSet -v
# 5 tests passing

# Router simplified
grep -A 50 "async def freeze_batch_set" app/routers/pricing_router.py | wc -l
# Should show ~30 LOC (down from 81)
```

**Outcome:**
- Router: 81 LOC → 30 LOC (-63%)
- Service: 60 LOC (pure business logic)
- Tests: 5 new unit tests

---

#### Task 2.3: Extract `clone_batch_set()` → `batch_set_service.py`

**Priority:** HIGH
**Complexity:** MEDIUM
**Time:** 2 days

**Steps:**
1. Add `clone_batch_set_with_batches()` to `batch_set_service.py`
2. Refactor router endpoint
3. Create service tests (6 tests)

**Validation:**
```bash
# Router simplified
grep -A 50 "async def clone_batch_set" app/routers/pricing_router.py | wc -l
# Should show ~20 LOC (down from 84)

# Tests pass
pytest tests/test_batch_set_service.py::TestCloneBatchSet -v
# 6 tests passing
```

**Outcome:**
- Router: 84 LOC → 20 LOC (-76%)
- Service: 65 LOC
- Tests: 6 new unit tests

---

#### Task 2.4: Extract `freeze_loose_batches_as_set()` → `batch_set_service.py`

**Priority:** HIGH
**Complexity:** HIGH
**Time:** 3 days

**Steps:**
1. Add `freeze_loose_batches_as_set()` to service
2. Refactor router endpoint
3. Create service tests (8 tests)
4. Full workflow integration tests

**Validation:**
```bash
# Router simplified (largest reduction!)
grep -A 60 "async def freeze_loose_batches_as_set" app/routers/pricing_router.py | wc -l
# Should show ~25 LOC (down from 99)

# Tests pass
pytest tests/test_batch_set_service.py::TestFreezeLooseBatches -v
# 8 tests passing

# Integration test
pytest tests/test_pricing_router.py::test_freeze_loose_batches_workflow -v
# Passes
```

**Outcome:**
- Router: 99 LOC → 25 LOC (-75%)
- Service: 75 LOC
- Tests: 8 new unit tests + integration

---

### 3.3 Phase 3: Post-Refactor Cleanup (2 days)

#### Task 3.1: Update Documentation

**Files to update:**

1. **CLAUDE.md**
```markdown
## VZORY

### Service Layer Pattern (NEW)
```python
# app/services/part_service.py
async def copy_material_geometry_from_item(part, db):
    """Business logic goes in services, not routers"""
    # ... implementation
```

**Pravidla:**
- Routers: HTTP handling only (<50 LOC/function)
- Services: Business logic (testable in isolation)
- Models: Data structures only
```

2. **ARCHITECTURE.md** - Add service layer section

3. **CHANGELOG.md**
```markdown
## [1.8.0] - 2026-02-XX

### Refactored
- Extracted business logic to service layer
- `part_service.py`: copy_material_geometry
- `batch_set_service.py`: freeze, clone, freeze_loose workflows
- Router functions reduced by 70% average

### Improved
- Test coverage: 94% → 95%+
- Longest function: 108 LOC → 30 LOC
- Service layer now testable in isolation
```

**Time:** 2 hours

---

#### Task 3.2: Delete Commented Code

**Search for commented code blocks:**
```bash
grep -rn "^#.*def " app/ --include="*.py"
grep -rn "^    # .*=" app/ --include="*.py" | wc -l
```

**Action:** Review and delete (should be minimal based on audit)

**Time:** 1 hour

---

#### Task 3.3: Run Linting + Type Checking

```bash
# Pylint
pylint app/ --disable=C0301,C0114,C0115,C0116
# Target: 9.0+ score

# MyPy (if using)
mypy app/ --ignore-missing-imports
# Target: 0 errors

# Black formatting
black app/ --check
# Target: Already formatted
```

**Fix any issues found.**

**Time:** 2 hours

---

## 4. Long-Term Migrations (v1.9.0+)

**Execute AFTER Vue migration complete, BEFORE v2.0 Orders module**

### 4.1 Float → Decimal Migration (PRIORITY: HIGH)

**Why Now:**
- Orders module will have invoices (legal requirement for exact decimals)
- Better to migrate before adding financial features
- Non-breaking if done carefully

**Affected Columns:** ~30 columns across 5 tables

**Migration Strategy:**

```python
# alembic/versions/YYYYMMDD_float_to_decimal.py
"""Convert Float to Numeric(10,2) for financial columns

Revision ID: abc123def456
Revises: previous_migration
Create Date: 2026-02-XX
"""

from alembic import op
import sqlalchemy as sa
from decimal import Decimal

def upgrade():
    # Batch operations for SQLite
    tables_columns = {
        'batches': ['unit_cost', 'total_cost', 'material_cost', 'machining_cost',
                    'setup_cost', 'overhead_cost', 'margin_cost', 'coop_cost',
                    'unit_price_frozen', 'total_price_frozen'],
        'parts': ['stock_price', 'stock_price_per_kg'],
        'material_items': ['price_per_kg', 'price_per_m', 'price_per_m2'],
        'price_categories': ['overhead_percentage', 'margin_percentage'],
        'work_centers': ['hourly_rate']
    }

    for table, columns in tables_columns.items():
        with op.batch_alter_table(table) as batch_op:
            for col in columns:
                batch_op.alter_column(
                    col,
                    existing_type=sa.Float(),
                    type_=sa.Numeric(10, 2),
                    existing_nullable=True,  # Check actual nullability
                    postgresql_using=f'{col}::numeric(10,2)'
                )

def downgrade():
    # Reverse: Numeric → Float
    # (omitted for brevity, reverse operations)
```

**Python Code Changes:**

```python
# app/models/batch.py
from decimal import Decimal
from sqlalchemy import Numeric

class Batch(Base):
    # BEFORE:
    # unit_cost: Mapped[float] = mapped_column(Float, default=0.0)

    # AFTER:
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal('0.00'))
```

**Service Layer Changes:**

```python
# app/services/price_calculator.py
from decimal import Decimal, ROUND_HALF_UP

def calculate_unit_cost(...) -> Decimal:
    # BEFORE: return float(...)
    # AFTER:
    cost = Decimal(material_cost + machining_cost + overhead)
    return cost.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
```

**Pydantic Schema Changes:**

```python
# app/schemas/batch.py
from decimal import Decimal

class BatchResponse(BaseModel):
    # BEFORE: unit_cost: float
    # AFTER:
    unit_cost: Decimal = Field(..., decimal_places=2)

    class Config:
        json_encoders = {
            Decimal: lambda v: float(v)  # JSON compatibility
        }
```

**Testing Strategy:**

```python
# tests/test_float_to_decimal_migration.py
def test_decimal_precision():
    """Test no rounding errors"""
    cost1 = Decimal('0.1')
    cost2 = Decimal('0.2')
    assert cost1 + cost2 == Decimal('0.3')  # ✅ Exact

def test_json_serialization():
    """Test API returns valid JSON"""
    batch = Batch(unit_cost=Decimal('123.45'))
    response = BatchResponse.model_validate(batch)
    json_str = response.model_dump_json()
    assert '"unit_cost":123.45' in json_str  # ✅ Float in JSON
```

**Rollback Plan:**

```bash
# If migration fails:
alembic downgrade -1

# If issues found in production:
1. Deploy hotfix (v1.8.1) reverting Decimal → Float
2. Fix migration script
3. Re-test in staging
4. Redeploy (v1.9.1)
```

**Timeline:** Week 4 (after Vue Phase 4 complete)

**Time Required:** 2-3 days (migration + testing + deployment)

---

### 4.2 SQLite FK CASCADE Migration (PRIORITY: MEDIUM)

**Why Later:**
- Requires table recreation (downtime)
- Current workaround works (soft delete = no hard FK cascade needed)
- Better after v2.0 when data structure stable

**Affected Tables:** 12 tables with FK constraints

**Migration Strategy:**

```python
# Recreate table with correct FK
def upgrade():
    for table in ['parts', 'operations', 'batches', ...]:
        # 1. Create table_new with correct FK
        op.execute(f'''
            CREATE TABLE {table}_new (
                ... columns ...
                FOREIGN KEY (material_item_id) REFERENCES material_items(id) ON DELETE CASCADE
            )
        ''')

        # 2. Copy data
        op.execute(f'INSERT INTO {table}_new SELECT * FROM {table}')

        # 3. Drop old table
        op.drop_table(table)

        # 4. Rename new → old
        op.rename_table(f'{table}_new', table)

        # 5. Recreate indexes
        op.create_index(...)
```

**Downtime Required:** 5-10 minutes (depends on data size)

**Risk:** HIGH (table recreation, data migration)

**Timeline:** v2.1.0+ (after Orders module stable)

**Decision:** DEFERRED (current soft delete approach sufficient)

---

## 5. Post-Vue Integration Cleanup

**Execute AFTER Vue Phase 4 complete (frontend deployed)**

### 5.1 Delete Alpine.js Frontend (WEEK 8+)

#### Task: Remove Legacy Frontend Files

**Files to DELETE:**

```bash
# Templates (Jinja2) - keep only error pages
rm app/templates/index.html
rm app/templates/workspace.html
rm app/templates/workspace_new.html
rm app/templates/parts_list.html
rm app/templates/settings.html
rm app/templates/parts/new.html
rm app/templates/parts/edit.html
rm app/templates/parts/pricing.html
rm app/templates/pricing/*.html
rm app/templates/machines/*.html
rm app/templates/admin/*.html

# Keep only:
# - app/templates/base.html (for error pages)
# - app/templates/errors/*.html

# JavaScript modules (ALL)
rm -rf app/static/js/modules/
rm -rf app/static/js/core/
rm app/static/js/crud_components.js
rm app/static/js/gestima.js

# Keep only vendor libs if needed by error pages
```

**Validation:**
```bash
# Count remaining templates
find app/templates -name "*.html" | wc -l
# Should show: ~5 (base + errors only)

# No JS modules
find app/static/js -name "*.js" | wc -l
# Should show: 0-2 (only vendor if needed)
```

**Git commit:**
```bash
git rm app/templates/workspace.html
git rm -r app/static/js/modules/
git commit -m "chore: Remove Alpine.js frontend (replaced by Vue SPA)

- Deleted 19 Jinja2 templates (kept error pages)
- Deleted 4,133 LOC JavaScript (Alpine.js modules)
- Vue SPA now serves all UI
- Alpine.js → Vue migration COMPLETE

Refs: VUE-MIGRATION.md Phase 4"
```

**Time:** 1 hour

**LOC Reduction:** -4,133 LOC JavaScript, -9,382 LOC templates = **-13,515 LOC total!**

---

### 5.2 Remove Pages Router (Optional)

**File:** `app/routers/pages_router.py`

**Current:** Serves Jinja2 templates (index, workspace, parts, etc.)

**After Vue:** Obsolete (Vue Router handles all pages)

**Action:**
```python
# app/main.py
# BEFORE:
app.include_router(pages_router)

# AFTER:
# app.include_router(pages_router)  # Removed - Vue SPA serves all pages
```

**Validation:**
```bash
# Test Vue SPA serves all routes
curl http://localhost:8000/ -I
# Should return: 200 OK (Vue index.html)

curl http://localhost:8000/parts -I
# Should return: 200 OK (Vue handles routing)

curl http://localhost:8000/api/parts/
# Should return: 200 OK (API still works)
```

**Git commit:**
```bash
git rm app/routers/pages_router.py
# Update app/main.py
git commit -m "chore: Remove pages_router.py (Vue SPA serves all UI)"
```

**Time:** 30 minutes

**LOC Reduction:** -200 LOC (pages_router.py)

---

### 5.3 Update gitignore + Clean Assets

**Files to ignore (if not already):**

```bash
# .gitignore additions
frontend/dist/
frontend/node_modules/
app/static/css/gestima.css  # If generated
*.pyc
__pycache__/
.vite/
```

**Clean unused CSS (if any):**
```bash
# Check if CSS files moved to Vue
ls -la app/static/css/
# If duplicated in frontend/src/assets/css/, delete from app/static/
```

**Time:** 15 minutes

---

## 6. Clean Slate Criteria

### 6.1 Code Quality Metrics

| Metric | Target | Validation Command |
|--------|--------|-------------------|
| **Test Coverage** | ≥95% | `pytest --cov=app --cov-report=term` |
| **Longest Function** | <50 LOC | `python scripts/check_function_lengths.py` |
| **Debug Prints** | 0 | `grep -rn "print(f" app/ --include="*.py"` |
| **TODO Comments** | 0 | `grep -rn "TODO\|HACK\|FIXME" app/` |
| **Dead Code Files** | 0 | Manual review |
| **Pylint Score** | ≥9.0 | `pylint app/` |
| **Alpine.js LOC** | 0 | `find app/static/js -name "*.js" \| wc -l` |
| **Jinja2 Templates** | <10 (errors only) | `find app/templates -name "*.html" \| wc -l` |

### 6.2 Architecture Validation

**Service Layer:**
- [ ] All business logic in `app/services/`
- [ ] Routers only handle HTTP (no logic >30 LOC)
- [ ] Services have unit tests (95%+ coverage)

**API Layer:**
- [ ] All endpoints documented (docstrings)
- [ ] Pydantic schemas for all inputs/outputs
- [ ] Consistent error handling (HTTPException)

**Database:**
- [ ] All migrations applied (Alembic)
- [ ] Indexes on deleted_at columns
- [ ] No N+1 queries (eager loading)

**Testing:**
- [ ] Unit tests for services
- [ ] Integration tests for routers
- [ ] E2E tests for critical workflows (Vue Playwright)

**Frontend:**
- [ ] Vue SPA serves all UI
- [ ] No Alpine.js code remains
- [ ] TypeScript strict mode passing
- [ ] Bundle size <200KB gzip

---

## 7. Validation Checklist

### 7.1 Pre-Cleanup Baseline

**Run BEFORE starting cleanup:**

```bash
# Save current metrics
echo "=== PRE-CLEANUP BASELINE ===" > cleanup_baseline.txt
echo "Date: $(date)" >> cleanup_baseline.txt
echo "" >> cleanup_baseline.txt

# LOC count
echo "Python LOC:" >> cleanup_baseline.txt
find app -name "*.py" -exec wc -l {} + | tail -1 >> cleanup_baseline.txt

echo "JavaScript LOC:" >> cleanup_baseline.txt
find app/static/js -name "*.js" -exec wc -l {} + | tail -1 >> cleanup_baseline.txt

echo "Template LOC:" >> cleanup_baseline.txt
find app/templates -name "*.html" -exec wc -l {} + | tail -1 >> cleanup_baseline.txt

# Test coverage
echo "" >> cleanup_baseline.txt
echo "Test coverage:" >> cleanup_baseline.txt
pytest --cov=app --cov-report=term | grep "TOTAL" >> cleanup_baseline.txt

# Long functions
echo "" >> cleanup_baseline.txt
echo "Functions >50 LOC:" >> cleanup_baseline.txt
python3 << 'EOF' >> cleanup_baseline.txt
import re
from pathlib import Path

count = 0
for py_file in Path("app").rglob("*.py"):
    with open(py_file) as f:
        lines = f.readlines()

    func_start = 0
    for i, line in enumerate(lines, 1):
        if re.match(r'^(async )?def \w+', line):
            if func_start > 0 and (i - func_start) > 50:
                count += 1
            func_start = i

print(f"Total: {count} functions")
EOF

# Debug prints
echo "" >> cleanup_baseline.txt
echo "Debug print statements:" >> cleanup_baseline.txt
grep -rn "print(f" app/ --include="*.py" | wc -l >> cleanup_baseline.txt

cat cleanup_baseline.txt
```

**Save output for comparison.**

---

### 7.2 Post-Cleanup Validation

**Run AFTER all cleanup tasks:**

```bash
# 1. Test suite passes
pytest tests/ -v
# Expected: 302/302 tests passing (or more with new tests)

# 2. Coverage check
pytest --cov=app --cov-report=term-missing
# Expected: ≥95%

# 3. No debug prints
grep -rn "print(f" app/ --include="*.py"
# Expected: (empty)

# 4. No TODO comments
grep -rn "TODO\|HACK\|FIXME" app/ --include="*.py"
# Expected: (empty)

# 5. Long functions check
python3 << 'EOF'
import re
from pathlib import Path

long_funcs = []
for py_file in Path("app").rglob("*.py"):
    with open(py_file) as f:
        lines = f.readlines()

    func_name = None
    func_start = 0
    for i, line in enumerate(lines, 1):
        if re.match(r'^(async )?def \w+', line):
            if func_start > 0:
                length = i - func_start
                if length > 50:
                    long_funcs.append((py_file, func_start, length, func_name))
            func_name = line.strip()
            func_start = i

if long_funcs:
    print(f"❌ Found {len(long_funcs)} functions >50 LOC:")
    for file, line, length, name in long_funcs:
        print(f"  {file}:{line} - {length} LOC - {name}")
else:
    print("✅ All functions <50 LOC")
EOF

# 6. Service layer exists
test -f app/services/part_service.py && echo "✅ part_service.py exists"
test -f app/services/batch_set_service.py && echo "✅ batch_set_service.py exists"

# 7. Service tests exist
test -f tests/test_part_service.py && echo "✅ test_part_service.py exists"
test -f tests/test_batch_set_service.py && echo "✅ test_batch_set_service.py exists"

# 8. Pylint score
pylint app/ --disable=C0301,C0114,C0115,C0116 | grep "Your code has been rated"
# Expected: rated at 9.0+/10

# 9. Alpine.js removed (after Vue complete)
find app/static/js/modules -name "*.js" 2>/dev/null | wc -l
# Expected: 0 (directory not found or empty)

# 10. LOC comparison
echo "=== POST-CLEANUP METRICS ==="
echo "Python LOC:"
find app -name "*.py" -exec wc -l {} + | tail -1

echo "JavaScript LOC:"
find app/static/js -name "*.js" -exec wc -l {} + 2>/dev/null | tail -1 || echo "0 (removed)"

echo "Template LOC:"
find app/templates -name "*.html" -exec wc -l {} + | tail -1

# Compare with baseline
echo ""
echo "Compare with: cleanup_baseline.txt"
```

---

### 7.3 Final Sign-Off Checklist

**Before declaring "Clean Slate Achieved":**

- [ ] **Code Quality**
  - [ ] Pylint score ≥9.0
  - [ ] Test coverage ≥95%
  - [ ] No functions >50 LOC
  - [ ] No debug print() statements
  - [ ] No TODO/HACK/FIXME comments

- [ ] **Architecture**
  - [ ] Service layer created (part_service, batch_set_service)
  - [ ] Routers refactored (thin HTTP handlers)
  - [ ] All tests passing (302+ tests)
  - [ ] Documentation updated (CLAUDE.md, ARCHITECTURE.md, CHANGELOG.md)

- [ ] **Frontend Migration**
  - [ ] Vue Phase 4 COMPLETE
  - [ ] Vue SPA serves all UI routes
  - [ ] Alpine.js code deleted (4,133 LOC removed)
  - [ ] Jinja2 templates deleted (except errors)
  - [ ] TypeScript compilation passing

- [ ] **Performance**
  - [ ] No N+1 queries
  - [ ] API responses <100ms (parts list)
  - [ ] Vue SPA bundle <200KB gzip
  - [ ] Lighthouse score >95

- [ ] **Security**
  - [ ] All endpoints have auth checks
  - [ ] Input validation (Pydantic schemas)
  - [ ] No SQL injection vectors
  - [ ] CSP + HSTS headers active

- [ ] **Documentation**
  - [ ] CHANGELOG.md updated
  - [ ] CLAUDE.md updated (service layer pattern)
  - [ ] VUE-MIGRATION.md marked COMPLETE
  - [ ] BACKEND-CLEANUP-GUIDE.md marked DONE

---

## 8. Timeline Summary

### Parallel Execution (2 weeks)

```
Week 1:
├─ Vue Phase 2 (Workspace modules)
└─ Backend Cleanup Phase 1-2 (debug prints, service extraction)

Week 2:
├─ Vue Phase 3 (Admin pages)
└─ Backend Cleanup Phase 3 (documentation, validation)

Week 3:
├─ Vue Phase 4 (deployment)
└─ Post-Vue Cleanup (delete Alpine.js)

Total: 3 weeks to "Clean Slate"
```

### Daily Breakdown

| Day | Vue Work | Backend Cleanup | Hours |
|-----|----------|-----------------|-------|
| **Mon** | Workspace shell | Fix debug prints | 8h |
| **Tue** | Parts list module | Extract copy_material_geometry | 8h |
| **Wed** | Part pricing module | Extract freeze_batch_set | 8h |
| **Thu** | Part operations | Extract clone_batch_set | 8h |
| **Fri** | Part material | Extract freeze_loose_batches | 8h |
| **Mon** | Batch sets module | Service tests | 8h |
| **Tue** | CRUD pages | Documentation update | 8h |
| **Wed** | Admin pages | Linting + validation | 8h |
| **Thu** | Testing | Testing | 8h |
| **Fri** | Deployment | Delete Alpine.js | 8h |

**Total effort:** 80 hours (2 weeks full-time)

---

## 9. Rollback Plan

### If Cleanup Fails

**Per-task rollback:**

```bash
# Rollback service extraction (if breaks)
git revert <commit-hash>
git push

# Rollback to pre-cleanup state
git checkout <baseline-tag>
```

**Tagging strategy:**

```bash
# Before cleanup
git tag -a v1.7.0-pre-cleanup -m "Baseline before backend cleanup"

# After Phase 1
git tag -a v1.7.1-debug-prints-fixed -m "Debug prints replaced with logging"

# After Phase 2
git tag -a v1.7.2-service-layer -m "Service layer extraction complete"

# After Phase 3
git tag -a v1.8.0-clean-slate -m "Clean slate achieved"
```

---

## 10. Success Criteria (Final)

### 10.1 Metrics Achieved

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Python LOC | 10,565 | <10,000 | -5%+ |
| JavaScript LOC | 4,133 | 0 | -100% |
| Template LOC | 9,382 | <500 | -95% |
| Test Coverage | 94% | 95%+ | +1%+ |
| Longest Function | 108 LOC | <50 LOC | -54% |
| Debug Prints | 10 | 0 | -100% |
| Service Tests | 0 | 27+ | NEW |

### 10.2 Architecture Goals Met

- ✅ Thin routers (HTTP only)
- ✅ Service layer (business logic)
- ✅ 95%+ test coverage
- ✅ Zero dead code
- ✅ Vue SPA frontend
- ✅ TypeScript strict mode
- ✅ Production-ready

### 10.3 "Clean Slate" Declaration

**When you can say:**

> "GESTIMA v1.8.0 má:
> - Čistý backend (service layer, <50 LOC/funkce)
> - Moderní frontend (Vue 3 SPA, TypeScript)
> - 95%+ test coverage
> - Zero technical debt
> - Production-ready pro v2.0 (Orders/Quotes/MES)"

**Git tag:**
```bash
git tag -a v1.8.0-clean-slate -m "Clean slate achieved - ready for v2.0

Backend:
- Service layer extracted (part_service, batch_set_service)
- All functions <50 LOC
- 95%+ test coverage
- Zero debug prints
- Pylint 9.0+

Frontend:
- Vue 3 SPA (TypeScript)
- Alpine.js removed (4,133 LOC deleted)
- Bundle <200KB gzip
- Lighthouse 95+

Next: v2.0 Orders & Quotes (VISION.md)"

git push --tags
```

---

## 11. Reference Files

**Full refactoring plan:** See Task agent output (section above)

**Critical files:**
- `/Users/lofas/Documents/__App_Claude/Gestima/app/services/part_service.py` (CREATE)
- `/Users/lofas/Documents/__App_Claude/Gestima/app/services/batch_set_service.py` (CREATE)
- `/Users/lofas/Documents/__App_Claude/Gestima/app/routers/pricing_router.py` (REFACTOR)
- `/Users/lofas/Documents/__App_Claude/Gestima/app/routers/parts_router.py` (REFACTOR)
- `/Users/lofas/Documents/__App_Claude/Gestima/tests/test_part_service.py` (CREATE)
- `/Users/lofas/Documents/__App_Claude/Gestima/tests/test_batch_set_service.py` (CREATE)

---

## 12. Quick Start Guide

**Want to start NOW? Here's the fastest path to clean slate:**

### Week 1: Quick Wins (Can do TODAY!)

```bash
# 1. Baseline metrics (5 min)
cd /Users/lofas/Documents/__App_Claude/Gestima
echo "=== BASELINE ===" > cleanup_baseline.txt
find app -name "*.py" -exec wc -l {} + | tail -1 >> cleanup_baseline.txt
pytest --cov=app --cov-report=term | grep "TOTAL" >> cleanup_baseline.txt

# 2. Fix debug prints (30 min)
# Edit app/services/material_parser.py:
# - Add: import logging; logger = logging.getLogger(__name__)
# - Replace all 10x print(f"🔍...) with logger.debug(...)

# 3. Remove unused import (5 min)
# Edit app/services/material_parser.py:
# - Check which types are used
# - Remove unused from import statement

# 4. Run tests
pytest tests/ -v
# Should pass: 302/302

# 5. Commit
git add app/services/material_parser.py
git commit -m "chore: Replace debug prints with structured logging

- Replaced 10x print() with logger.debug()
- Removed unused imports
- Production-ready logging

Refs: BACKEND-CLEANUP-GUIDE.md Task 1.1-1.2"
```

**Time:** 1 hour
**Impact:** Production-ready logging ✅

---

### Week 2-3: Service Layer (Parallel with Vue)

```bash
# Week 2: While Vue Phase 2 runs
# - Extract copy_material_geometry (Day 1)
# - Extract freeze_batch_set (Day 2-3)
# - Extract clone_batch_set (Day 4-5)

# Week 3: While Vue Phase 3 runs
# - Extract freeze_loose_batches_as_set (Day 1-3)
# - Update docs (Day 4)
# - Validation (Day 5)

# Follow detailed plan in Section 3.2
```

**Time:** 2 weeks parallel
**Impact:** Service layer complete, <50 LOC/function ✅

---

### Week 4: Post-Vue Cleanup

```bash
# After Vue Phase 4 deployed

# Delete Alpine.js (1 hour)
git rm app/templates/workspace.html app/templates/workspace_new.html
git rm -r app/static/js/modules/
git commit -m "chore: Remove Alpine.js frontend (replaced by Vue SPA)"

# Final validation
pytest --cov=app --cov-report=term
# Expected: 95%+ coverage

# Tag clean slate
git tag -a v1.8.0-clean-slate -m "Clean slate achieved"
git push --tags
```

**Time:** 2 hours
**Impact:** -13,515 LOC removed, clean slate ✅

---

### DONE! You can now say:

> **"GESTIMA v1.8.0 = Zero technical debt, ready for v2.0!"**

---

**Document End**

*Generated: 2026-01-29*
*Author: Roy (AI Dev Team)*
*Status: ULTIMATE EDITION - All audits merged, zero problems when followed*
*Timeline: 3 weeks parallel with Vue migration*

---

**"Have you tried turning it off and on again?"**
= Clean slate = Vyhoď mrtvoly, extractuj services, nasaď Vue, ready for v2.0.

**Když budeš postupovat podle tohoto guide:**
- ✅ Zero dead code
- ✅ Zero debug prints
- ✅ Thin routers (<50 LOC)
- ✅ Service layer (testable)
- ✅ 95%+ coverage
- ✅ Float→Decimal ready (v1.9.0)
- ✅ Vue SPA deployed
- ✅ **JEDINÝ problém nebude!**
