# GESTIMA Vue SPA Migration Guide

## 🔥 FULL STACK FRESH START 🔥

**Version:** 2.0
**Date:** 2026-01-29
**Status:** APPROVED
**Author:** Roy (AI Dev Team)
**Scope:** Frontend rewrite + Backend review & optimization

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Backend Code Review & Optimization](#2-backend-code-review--optimization)
3. [Current State Inventory](#3-current-state-inventory)
4. [Vue SPA Architecture](#4-vue-spa-architecture)
5. [Component Mapping](#5-component-mapping)
6. [API Client Design](#6-api-client-design)
7. [Store (Pinia) Design](#7-store-pinia-design)
8. [Router Design](#8-router-design)
9. [Migration Phases](#9-migration-phases)
10. [Performance Requirements](#10-performance-requirements)
11. [Testing Strategy](#11-testing-strategy)
12. [Deployment Strategy](#12-deployment-strategy)
13. [Rollback Plan](#13-rollback-plan)

---

## 1. Executive Summary

### Decision

**GESTIMA FULL STACK REFRESH: Vue 3 SPA + Backend Optimization**

### Scope

| Layer | Action |
|-------|--------|
| **Frontend** | Complete rewrite: Alpine.js → Vue 3 SPA |
| **Backend** | Review & optimize: Routers, Services, Models |
| **Database** | Keep as-is (SQLite + existing schema) |
| **API** | Keep endpoints, improve implementation |

### Důvody

**Frontend (Vue 3):**
1. **Profesionální SPA** - Žádný DIY router (800 LOC workspace-controller.js)
2. **Zero workaroundy** - Eliminace L-013, L-017, L-018, L-019, L-020, L-021
3. **Performance** - 41ms transitions (vs 80ms Alpine.js)
4. **Žádné problikávání** - Full SPA, no page reloads
5. **Long-term** - Připravenost na v4.0 MES (real-time, offline)
6. **TypeScript** - Compile-time type safety

**Backend (Optimization):**
1. **Code quality** - Odstranit duplicity, nepoužívaný kód
2. **Performance** - Identifikovat a opravit N+1 queries
3. **Security** - Review input validation, SQL injection prevention
4. **Consistency** - Jednotný error handling, response format
5. **Documentation** - Aktuální docstrings, OpenAPI schema

### Timeline

```
Week 1-2: Foundation + Backend Review (setup, auth, routers audit)
Week 3-4: Workspace migration + Services optimization
Week 5-6: Remaining pages + Final backend cleanup
Week 7-8: Testing & deployment
─────────────────────────────────────────
Total: 6-8 týdnů
```

### Philosophy

> **"Když už to děláme, uděláme to POŘÁDNĚ."**
>
> Toto není jen frontend rewrite. Je to příležitost pro FRESH START:
> - Projít KAŽDÝ router endpoint
> - Zkontrolovat KAŽDOU service funkci
> - Odstranit VŠECHEN legacy code
> - Vytvořit ČISTOU, maintainable codebase

---

## 2. Backend Code Review & Optimization

### 2.1 Routers Review Checklist

**Pro KAŽDÝ endpoint v každém routeru:**

```
□ Endpoint je stále potřebný? (není obsolete)
□ Správný HTTP method (GET/POST/PUT/DELETE)
□ Správné status codes (200, 201, 204, 400, 401, 403, 404, 409, 422, 500)
□ Input validation (Pydantic schema)
□ Output serialization (response_model)
□ Error handling (HTTPException s detailním message)
□ Auth check (get_current_user dependency)
□ Role check (admin/operator/viewer)
□ Eager loading (selectinload pro relationships)
□ Pagination (skip/limit pro list endpoints)
□ Optimistic locking (version field pro PUT)
□ Audit trail (created_by, updated_by)
□ Soft delete (deleted_at, deleted_by)
□ Docstring aktuální
□ OpenAPI tags správné
```

### 2.2 Routers to Review

| Router | Endpoints | Priority | Status |
|--------|-----------|----------|--------|
| `auth_router.py` | 3 | 🔴 HIGH | ⬜ TODO |
| `parts_router.py` | 12 | 🔴 HIGH | ⬜ TODO |
| `operations_router.py` | 6 | 🔴 HIGH | ⬜ TODO |
| `batches_router.py` | 8 | 🔴 HIGH | ⬜ TODO |
| `pricing_router.py` | 12 | 🔴 HIGH | ⬜ TODO |
| `work_centers_router.py` | 7 | 🟡 MED | ⬜ TODO |
| `materials_router.py` | 15 | 🟡 MED | ⬜ TODO |
| `features_router.py` | 5 | 🟡 MED | ⬜ TODO |
| `admin_router.py` | 10 | 🟢 LOW | ⬜ TODO |
| `config_router.py` | 3 | 🟢 LOW | ⬜ TODO |
| `data_router.py` | 4 | 🟢 LOW | ⬜ TODO |
| `misc_router.py` | 2 | 🟢 LOW | ⬜ TODO |

**Total: 87 endpoints to review**

### 2.3 Common Issues to Fix

#### Issue 1: Inconsistent Error Handling

```python
# ❌ BEFORE (inconsistent):
if not part:
    raise HTTPException(404)  # Missing detail

if not part:
    raise HTTPException(status_code=404, detail="Part not found")  # Different style

# ✅ AFTER (consistent):
if not part:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Part with number {part_number} not found"
    )
```

#### Issue 2: Missing Eager Loading

```python
# ❌ BEFORE (N+1 query):
parts = await db.execute(select(Part))
for part in parts:
    print(part.material_item.name)  # N+1!

# ✅ AFTER (eager load):
parts = await db.execute(
    select(Part)
    .options(selectinload(Part.material_item))
)
```

#### Issue 3: Duplicated Transaction Handling

```python
# ❌ BEFORE (duplicated try/except):
try:
    db.add(entity)
    await db.commit()
    await db.refresh(entity)
except IntegrityError:
    await db.rollback()
    raise HTTPException(409, "Duplicate")

# ✅ AFTER (use safe_commit helper):
await safe_commit(db, entity, "Entity already exists")
```

#### Issue 4: Missing Pagination

```python
# ❌ BEFORE (returns all):
@router.get("/items")
async def list_items(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Item))
    return result.scalars().all()  # Could be 10,000 items!

# ✅ AFTER (paginated):
@router.get("/items")
async def list_items(
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500)
):
    result = await db.execute(
        select(Item)
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()
```

#### Issue 5: Weak Input Validation

```python
# ❌ BEFORE (no validation):
class PartCreate(BaseModel):
    name: str
    quantity: int

# ✅ AFTER (proper validation):
class PartCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    quantity: int = Field(..., gt=0, le=1_000_000)

    @field_validator('name')
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError('Name cannot be empty or whitespace')
        return v.strip()
```

### 2.4 Services Review Checklist

**Pro KAŽDOU service funkci:**

```
□ Single responsibility (jedna funkce = jedna věc)
□ No side effects (nepřepisuje neočekávané data)
□ Proper error handling (raise, ne return None)
□ Type hints (input a output types)
□ Docstring s příklady
□ Unit testable (no hidden dependencies)
□ No business logic in routers (patří sem)
□ No DB queries duplicated (centralize zde)
```

### 2.5 Services to Review

| Service | Functions | Priority | Status |
|---------|-----------|----------|--------|
| `price_calculator.py` | ~10 | 🔴 HIGH | ⬜ TODO |
| `batch_service.py` | ~8 | 🔴 HIGH | ⬜ TODO |
| `part_service.py` | ~6 | 🟡 MED | ⬜ TODO |
| `material_service.py` | ~5 | 🟡 MED | ⬜ TODO |
| `auth_service.py` | ~4 | 🟢 LOW | ⬜ TODO |

### 2.6 Models Review Checklist

**Pro KAŽDÝ model:**

```
□ Správné typy (String length, Integer constraints)
□ Nullable fields správně nastavené
□ Default values smysluplné
□ Relationships oboustranné (back_populates)
□ Indexes na často queryované sloupce
□ Unique constraints kde potřeba
□ Soft delete fields (deleted_at, deleted_by)
□ Audit fields (created_at, created_by, updated_at, updated_by)
□ Version field pro optimistic locking
□ __repr__ pro debugging
```

### 2.7 Schemas Review Checklist

**Pro KAŽDÉ Pydantic schema:**

```
□ Field validace (min/max length, gt/ge/lt/le)
□ Optional vs Required správně
□ Default values smysluplné
□ Config class (from_attributes = True)
□ Example values pro OpenAPI
□ Computed fields kde potřeba
□ Validator functions pro complex rules
```

### 2.8 What to Look For (Red Flags)

| Red Flag | Action |
|----------|--------|
| `# TODO` comments | Resolve or create issue |
| `# HACK` comments | Refactor properly |
| `# FIXME` comments | Fix it now |
| Commented-out code | Delete it |
| Unused imports | Remove |
| Unused functions | Remove |
| Duplicate code | Extract to helper |
| Magic numbers | Create constants |
| Long functions (>50 LOC) | Split into smaller |
| Deep nesting (>3 levels) | Refactor |
| No type hints | Add them |
| No docstrings | Add them |
| Bare `except:` | Specify exception type |
| `print()` statements | Use logger |
| Hardcoded values | Use config/env |

### 2.9 Backend Optimization Goals

| Metric | Current | Target |
|--------|---------|--------|
| Avg endpoint response | ~150ms | <100ms |
| List endpoints (100 items) | ~300ms | <150ms |
| Code coverage | ~60% | >80% |
| Pylint score | Unknown | >9.0 |
| TODO comments | Unknown | 0 |
| Unused code | Unknown | 0 |
| Duplicate code | Unknown | 0 |

### 2.10 Backend Review Output

Po review každého routeru vytvořím:

```markdown
## Router: parts_router.py

### Endpoints Reviewed: 12/12 ✅

### Issues Found:
1. ❌ GET /parts/ - missing pagination
2. ⚠️ PUT /parts/{id} - weak validation
3. ✅ POST /parts/ - OK

### Changes Made:
- Added pagination to list endpoint
- Added Field validation to PartUpdate schema
- Fixed N+1 query in get_part_full

### Performance Before/After:
- GET /parts/: 450ms → 120ms
- GET /parts/{id}/full: 280ms → 95ms

### Tests Added:
- test_parts_pagination
- test_parts_validation_error
```

---

## 3. Current State Inventory

### 2.1 Templates (Jinja2)

```
app/templates/
├── base.html                    # 159 LOC - Base template (all extend)
├── index.html                   # 179 LOC - Dashboard
├── workspace.html               # 1,457 LOC - Multi-panel workspace ⭐
├── workspace_new.html           # 731 LOC - Workspace skeleton
├── parts_list.html              # 145 LOC - Parts list
├── machines_list.html           # 178 LOC - Machines list
├── settings.html                # 178 LOC - User settings
├── macros.html                  # 273 LOC - Reusable form macros
│
├── auth/
│   └── login.html               # 237 LOC - Login page
│
├── parts/
│   ├── new.html                 # 291 LOC - Create part form
│   ├── edit.html                # 2,128 LOC - Part editor ⭐ (LARGEST)
│   └── pricing.html             # 305 LOC - Part pricing view
│
├── machines/
│   └── edit.html                # 167 LOC - Edit machine
│
├── pricing/
│   ├── batch_sets.html          # 372 LOC - Batch sets list
│   └── batch_set_detail.html    # 391 LOC - Batch set detail
│
└── admin/
    ├── master_data.html         # 1,221 LOC - Master data admin ⭐
    ├── material_catalog.html    # 668 LOC - Material catalog
    ├── material_norm_form.html  # 263 LOC - Material norm form
    └── material_norms_simple.html # 39 LOC - Simplified norms

TOTAL: 19 templates, 9,382 LOC
```

**Priorita migrace (podle komplexity):**

| Priority | Template | LOC | Complexity | Vue Component |
|----------|----------|-----|------------|---------------|
| 🔴 HIGH | parts/edit.html | 2,128 | Very High | PartEditor.vue |
| 🔴 HIGH | workspace.html | 1,457 | High | Workspace.vue |
| 🟡 MED | admin/master_data.html | 1,221 | Medium | MasterData.vue |
| 🟡 MED | workspace_new.html | 731 | Medium | (merge with Workspace) |
| 🟡 MED | admin/material_catalog.html | 668 | Medium | MaterialCatalog.vue |
| 🟢 LOW | pricing/batch_set_detail.html | 391 | Low | BatchSetDetail.vue |
| 🟢 LOW | pricing/batch_sets.html | 372 | Low | BatchSetsList.vue |
| 🟢 LOW | parts/pricing.html | 305 | Low | PartPricing.vue |
| 🟢 LOW | parts/new.html | 291 | Low | PartCreate.vue |
| 🟢 LOW | auth/login.html | 237 | Low | LoginView.vue |
| 🟢 LOW | index.html | 179 | Low | Dashboard.vue |
| 🟢 LOW | settings.html | 178 | Low | Settings.vue |
| 🟢 LOW | machines_list.html | 178 | Low | MachinesList.vue |
| 🟢 LOW | machines/edit.html | 167 | Low | MachineEdit.vue |
| 🟢 LOW | parts_list.html | 145 | Low | PartsList.vue |

### 2.2 JavaScript Modules

```
app/static/js/
├── gestima.js                   # 190 LOC - Main utilities
├── crud_components.js           # 161 LOC - CRUD helpers
│
├── core/                        # Workspace framework (1,394 LOC)
│   ├── workspace-controller.js  # 753 LOC - Panel management ⭐
│   ├── link-manager.js          # 305 LOC - Inter-module pub/sub
│   ├── module-registry.js       # 227 LOC - Module factory
│   └── module-interface.js      # 109 LOC - Base interface
│
├── modules/                     # Workspace modules (2,388 LOC)
│   ├── batch-sets.js            # 701 LOC - Batch sets pricing
│   ├── part-material.js         # 497 LOC - Part materials
│   ├── part-operations.js       # 462 LOC - Part operations
│   ├── part-pricing.js          # 460 LOC - Part pricing
│   └── parts-list.js            # 268 LOC - Parts list
│
└── vendor/
    ├── alpine.min.js            # Alpine.js 3
    └── htmx.min.js              # HTMX (unused)

TOTAL: 4,133 LOC (excluding vendors)
```

**Module → Vue Component Mapping:**

| Alpine Module | LOC | Vue Component | Vue LOC (est.) |
|---------------|-----|---------------|----------------|
| workspace-controller.js | 753 | Workspace.vue + Vue Router | ~150 |
| link-manager.js | 305 | Pinia stores | ~100 |
| module-registry.js | 227 | (eliminated) | 0 |
| module-interface.js | 109 | (eliminated) | 0 |
| batch-sets.js | 701 | BatchSetsModule.vue | ~400 |
| part-material.js | 497 | PartMaterial.vue | ~300 |
| part-operations.js | 462 | PartOperations.vue | ~280 |
| part-pricing.js | 460 | PartPricing.vue | ~280 |
| parts-list.js | 268 | PartsList.vue | ~180 |

**Expected LOC reduction: 4,133 → ~1,690 (-59%)**

### 2.3 CSS Files

```
app/static/css/
├── gestima.css      # Master import (all others)
├── variables.css    # CSS custom properties (design tokens)
├── base.css         # Base HTML elements
├── layout.css       # Grid, flexbox
├── components.css   # Buttons, cards, modals
├── operations.css   # Operation type icons
└── forms.css        # Form inputs, validation

TOTAL: 7 files, ~21 KB
```

**CSS Strategy:** Preserve and import existing CSS into Vue. No rewrite needed.

### 2.4 Anti-patterns to Eliminate

| ID | Problem | Alpine Workaround | Vue Solution |
|----|---------|-------------------|--------------|
| L-013 | Debounce race | Sequence tracking | Vue reactivity |
| L-017 | Alpine Proxy | JSON.parse snapshot | Vue reactive() |
| L-018 | select() broken | data-fresh pattern | @focus handler |
| L-019 | Data loss unload | beforeunload hack | Vue lifecycle |
| L-020 | Module collision | window.foo check | ES modules |
| L-021 | String/number | parseInt manual | TypeScript |

**All 6 anti-patterns ELIMINATED by Vue + TypeScript.**

### 2.5 API Endpoints (Vue will consume)

#### Authentication
```
POST /api/auth/login     → Login, set HttpOnly cookie
POST /api/auth/logout    → Logout, clear cookie
GET  /api/auth/me        → Current user info
```

#### Parts
```
GET    /api/parts/                         → List parts (paginated)
GET    /api/parts/search?search=X          → Search parts
GET    /api/parts/{part_number}            → Get part
GET    /api/parts/{part_number}/full       → Get part with relations
POST   /api/parts/                         → Create part
PUT    /api/parts/{part_number}            → Update part
DELETE /api/parts/{part_number}            → Delete part
POST   /api/parts/{part_number}/duplicate  → Clone part
GET    /api/parts/{part_number}/pricing    → Price breakdown
GET    /api/parts/{part_number}/stock-cost → Material cost
```

#### Operations
```
GET    /api/operations/part/{part_id}      → List operations for part
GET    /api/operations/{operation_id}      → Get operation
POST   /api/operations/                    → Create operation
PUT    /api/operations/{operation_id}      → Update operation
DELETE /api/operations/{operation_id}      → Delete operation
```

#### Features (Operation Steps)
```
GET    /api/features/operation/{op_id}     → List features
GET    /api/features/{feature_id}          → Get feature
POST   /api/features/                      → Create feature
PUT    /api/features/{feature_id}          → Update feature
DELETE /api/features/{feature_id}          → Delete feature
```

#### Batches
```
GET    /api/batches/part/{part_id}         → List batches for part
GET    /api/batches/{batch_number}         → Get batch
POST   /api/batches/                       → Create batch
DELETE /api/batches/{batch_number}         → Delete batch
POST   /api/batches/{batch_number}/freeze  → Freeze batch
POST   /api/batches/{batch_number}/clone   → Clone batch
POST   /api/batches/{batch_number}/recalculate → Recalculate
```

#### Batch Sets
```
GET    /api/pricing/batch-sets             → List all sets
GET    /api/pricing/part/{part_id}/batch-sets → Sets for part
GET    /api/pricing/batch-sets/{set_id}    → Get set with batches
POST   /api/pricing/batch-sets             → Create set
PUT    /api/pricing/batch-sets/{set_id}    → Update set
DELETE /api/pricing/batch-sets/{set_id}    → Delete set
POST   /api/pricing/batch-sets/{set_id}/freeze → Freeze set
POST   /api/pricing/batch-sets/{set_id}/batches → Add batch
DELETE /api/pricing/batch-sets/{set_id}/batches/{batch_id} → Remove
```

#### Work Centers
```
GET    /api/work-centers/                  → List work centers
GET    /api/work-centers/search?search=X   → Search
GET    /api/work-centers/types             → List types (enum)
GET    /api/work-centers/{number}          → Get work center
POST   /api/work-centers/                  → Create
PUT    /api/work-centers/{number}          → Update
DELETE /api/work-centers/{number}          → Delete
```

#### Materials
```
GET    /api/materials/groups               → List material groups
GET    /api/materials/items                → List stock items
GET    /api/materials/items/{number}       → Get stock item
POST   /api/materials/items                → Create stock item
PUT    /api/materials/items/{number}       → Update stock item
POST   /api/materials/parse                → Smart parse description
GET    /api/materials/price-categories     → List price categories
GET    /api/materials/price-tiers          → List price tiers
```

#### Admin
```
GET    /api/admin/material-groups          → List groups
GET    /api/admin/material-norms/search    → Search norms
POST   /api/admin/material-norms           → Create norm
PUT    /api/admin/material-norms/{id}      → Update norm
DELETE /api/admin/material-norms/{id}      → Delete norm
```

#### Reference Data
```
GET    /api/data/work-centers              → Dropdown: work centers
GET    /api/data/materials                 → Dropdown: material groups
GET    /api/data/feature-types             → Dropdown: feature types
GET    /api/data/stock-price               → Live material price calc
```

#### Config
```
GET    /api/config/                        → List all config
GET    /api/config/{key}                   → Get config value
PUT    /api/config/{key}                   → Update config
```

#### Misc
```
GET    /api/misc/fact                      → Random article (RSS)
GET    /api/misc/weather                   → Weather data
```

**Total: 60+ API endpoints, all JSON responses, ready for Vue.**

---

## 4. Vue SPA Architecture

### 3.1 Project Structure

```
gestima/
├── backend/                         # EXISTING (no changes)
│   ├── app/
│   │   ├── routers/
│   │   ├── services/
│   │   ├── models/
│   │   └── schemas/
│   ├── gestima.py
│   └── gestima.db
│
└── frontend/                        # NEW (Vue SPA)
    ├── index.html                   # Entry point
    ├── vite.config.ts               # Vite configuration
    ├── tsconfig.json                # TypeScript config
    ├── package.json                 # Dependencies
    │
    ├── public/                      # Static assets (copied as-is)
    │   └── favicon.ico
    │
    └── src/
        ├── main.ts                  # Vue app entry
        ├── App.vue                  # Root component
        │
        ├── assets/                  # Processed assets
        │   └── css/
        │       ├── variables.css    # (from existing)
        │       ├── base.css
        │       ├── layout.css
        │       ├── components.css
        │       ├── operations.css
        │       └── forms.css
        │
        ├── api/                     # API client layer
        │   ├── client.ts            # Axios instance + interceptors
        │   ├── auth.ts              # Auth endpoints
        │   ├── parts.ts             # Parts endpoints
        │   ├── operations.ts        # Operations endpoints
        │   ├── batches.ts           # Batches endpoints
        │   ├── batchSets.ts         # Batch sets endpoints
        │   ├── workCenters.ts       # Work centers endpoints
        │   ├── materials.ts         # Materials endpoints
        │   └── admin.ts             # Admin endpoints
        │
        ├── types/                   # TypeScript interfaces
        │   ├── index.ts             # Re-exports
        │   ├── auth.ts              # User, LoginRequest, etc.
        │   ├── part.ts              # Part, PartCreate, etc.
        │   ├── operation.ts         # Operation, etc.
        │   ├── batch.ts             # Batch, BatchSet, etc.
        │   ├── workCenter.ts        # WorkCenter, etc.
        │   └── material.ts          # MaterialItem, etc.
        │
        ├── stores/                  # Pinia stores
        │   ├── auth.ts              # Auth state + actions
        │   ├── parts.ts             # Parts state
        │   ├── operations.ts        # Operations state
        │   ├── batches.ts           # Batches state
        │   ├── batchSets.ts         # Batch sets state
        │   ├── workCenters.ts       # Work centers state
        │   ├── materials.ts         # Materials state
        │   ├── workspace.ts         # Workspace panel state
        │   └── ui.ts                # UI state (toasts, loading)
        │
        ├── router/                  # Vue Router
        │   └── index.ts             # Route definitions
        │
        ├── composables/             # Reusable composition functions
        │   ├── useApi.ts            # Generic API call wrapper
        │   ├── useOptimisticLock.ts # Version handling
        │   ├── useDebounce.ts       # Debounced values
        │   ├── useToast.ts          # Toast notifications
        │   └── useConfirm.ts        # Confirmation dialogs
        │
        ├── components/              # Reusable components
        │   ├── layout/
        │   │   ├── AppHeader.vue
        │   │   ├── AppSidebar.vue
        │   │   └── AppFooter.vue
        │   │
        │   ├── ui/
        │   │   ├── Button.vue
        │   │   ├── Input.vue
        │   │   ├── Select.vue
        │   │   ├── Modal.vue
        │   │   ├── Toast.vue
        │   │   ├── Spinner.vue
        │   │   ├── DataTable.vue
        │   │   ├── Pagination.vue
        │   │   └── ConfirmDialog.vue
        │   │
        │   ├── forms/
        │   │   ├── FormField.vue
        │   │   ├── FormGroup.vue
        │   │   └── ValidationError.vue
        │   │
        │   └── workspace/
        │       ├── WorkspaceTabs.vue
        │       ├── WorkspacePanel.vue
        │       └── WorkspaceLayout.vue
        │
        └── views/                   # Page components
            ├── auth/
            │   └── LoginView.vue
            │
            ├── dashboard/
            │   └── DashboardView.vue
            │
            ├── parts/
            │   ├── PartsListView.vue
            │   ├── PartCreateView.vue
            │   ├── PartEditView.vue
            │   └── PartPricingView.vue
            │
            ├── workspace/
            │   ├── WorkspaceView.vue
            │   └── modules/
            │       ├── PartPricingModule.vue
            │       ├── BatchSetsModule.vue
            │       ├── PartOperationsModule.vue
            │       ├── PartMaterialModule.vue
            │       └── PartsListModule.vue
            │
            ├── pricing/
            │   ├── BatchSetsListView.vue
            │   └── BatchSetDetailView.vue
            │
            ├── workCenters/
            │   ├── WorkCentersListView.vue
            │   └── WorkCenterEditView.vue
            │
            ├── admin/
            │   ├── MasterDataView.vue
            │   ├── MaterialCatalogView.vue
            │   └── MaterialNormsView.vue
            │
            └── settings/
                └── SettingsView.vue
```

### 3.2 Technology Stack

| Layer | Technology | Version | Purpose |
|-------|------------|---------|---------|
| **Framework** | Vue 3 | ^3.4 | Composition API |
| **Build** | Vite | ^5.0 | Dev server, bundling |
| **Language** | TypeScript | ^5.3 | Type safety |
| **Routing** | Vue Router | ^4.2 | SPA navigation |
| **State** | Pinia | ^2.1 | State management |
| **HTTP** | Axios | ^1.6 | API calls |
| **Forms** | VeeValidate | ^4.12 | Form validation |
| **Testing** | Vitest | ^1.2 | Unit tests |
| **E2E** | Playwright | ^1.41 | E2E tests |

### 3.3 Key Architectural Decisions

#### 3.3.1 Composition API (not Options API)

```vue
<!-- ✅ CORRECT: Composition API -->
<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { usePartsStore } from '@/stores/parts';

const store = usePartsStore();
const searchQuery = ref('');

const filteredParts = computed(() =>
  store.parts.filter(p => p.name.includes(searchQuery.value))
);

onMounted(() => store.fetchParts());
</script>

<!-- ❌ WRONG: Options API (don't use) -->
<script>
export default {
  data() { return { searchQuery: '' } },
  computed: { ... },
  mounted() { ... }
}
</script>
```

#### 3.3.2 TypeScript Strict Mode

```typescript
// tsconfig.json
{
  "compilerOptions": {
    "strict": true,
    "noImplicitAny": true,
    "strictNullChecks": true
  }
}
```

#### 3.3.3 Centralized API Client

```typescript
// src/api/client.ts
import axios from 'axios';

export const apiClient = axios.create({
  baseURL: '/api',
  withCredentials: true, // HttpOnly cookies
  headers: { 'Content-Type': 'application/json' }
});

// Response interceptor for errors
apiClient.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 401) {
      // Redirect to login
      window.location.href = '/login';
    }
    if (error.response?.status === 409) {
      // Optimistic lock conflict
      throw new OptimisticLockError(error.response.data);
    }
    throw error;
  }
);
```

#### 3.3.4 Optimistic Locking Pattern

```typescript
// src/composables/useOptimisticLock.ts
export function useOptimisticLock<T extends { version: number }>() {
  const update = async (
    id: number,
    data: Partial<T>,
    version: number,
    updateFn: (id: number, data: Partial<T> & { version: number }) => Promise<T>
  ): Promise<T> => {
    try {
      return await updateFn(id, { ...data, version });
    } catch (error) {
      if (error instanceof OptimisticLockError) {
        // Show conflict dialog
        const action = await showConflictDialog();
        if (action === 'refresh') {
          // Refresh and retry
        }
      }
      throw error;
    }
  };

  return { update };
}
```

---

## 5. Component Mapping

### 4.1 Template → Vue View Mapping

| Jinja2 Template | Vue View | Route |
|-----------------|----------|-------|
| auth/login.html | LoginView.vue | /login |
| index.html | DashboardView.vue | / |
| parts_list.html | PartsListView.vue | /parts |
| parts/new.html | PartCreateView.vue | /parts/new |
| parts/edit.html | PartEditView.vue | /parts/:partNumber/edit |
| parts/pricing.html | PartPricingView.vue | /parts/:partNumber/pricing |
| workspace.html | WorkspaceView.vue | /workspace |
| pricing/batch_sets.html | BatchSetsListView.vue | /pricing/batch-sets |
| pricing/batch_set_detail.html | BatchSetDetailView.vue | /pricing/batch-sets/:id |
| machines_list.html | WorkCentersListView.vue | /work-centers |
| machines/edit.html | WorkCenterEditView.vue | /work-centers/:number/edit |
| settings.html | SettingsView.vue | /settings |
| admin/master_data.html | MasterDataView.vue | /admin/master-data |
| admin/material_catalog.html | MaterialCatalogView.vue | /admin/materials |
| admin/material_norm_form.html | MaterialNormsView.vue | /admin/norms |

### 4.2 Alpine Module → Vue Component Mapping

| Alpine Module | Vue Component | Location |
|---------------|---------------|----------|
| workspace-controller.js | WorkspaceView.vue | views/workspace/ |
| link-manager.js | Pinia stores | stores/*.ts |
| module-registry.js | (eliminated) | - |
| module-interface.js | (eliminated) | - |
| batch-sets.js | BatchSetsModule.vue | views/workspace/modules/ |
| part-material.js | PartMaterialModule.vue | views/workspace/modules/ |
| part-operations.js | PartOperationsModule.vue | views/workspace/modules/ |
| part-pricing.js | PartPricingModule.vue | views/workspace/modules/ |
| parts-list.js | PartsListModule.vue | views/workspace/modules/ |

### 4.3 Jinja2 Macros → Vue Components

| Jinja2 Macro | Vue Component | Purpose |
|--------------|---------------|---------|
| `{% call form_field() %}` | FormField.vue | Form field wrapper |
| `{% call input_text() %}` | Input.vue | Text input |
| `{% call input_number() %}` | Input.vue (type="number") | Number input |
| `{% call select() %}` | Select.vue | Dropdown select |
| `{% call textarea() %}` | Textarea.vue | Multiline text |

### 4.4 Global Utilities Mapping

| Alpine/JS Utility | Vue Equivalent |
|-------------------|----------------|
| `window.showToast()` | `useToast()` composable |
| `window.debounce()` | `useDebouncedRef()` composable |
| `window.LinkManager` | Pinia stores |
| `Alpine.store()` | Pinia stores |

---

## 6. API Client Design

### 5.1 Client Setup

```typescript
// src/api/client.ts
import axios, { AxiosError, AxiosResponse } from 'axios';
import { useAuthStore } from '@/stores/auth';
import { useUiStore } from '@/stores/ui';
import router from '@/router';

// Custom error classes
export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public data?: any
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

export class OptimisticLockError extends ApiError {
  constructor(data: any) {
    super('Data byla změněna jiným uživatelem', 409, data);
    this.name = 'OptimisticLockError';
  }
}

export class ValidationError extends ApiError {
  constructor(data: any) {
    super('Validation failed', 422, data);
    this.name = 'ValidationError';
  }
}

// Create axios instance
export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  withCredentials: true, // Important for HttpOnly cookies
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
  }
});

// Request interceptor
apiClient.interceptors.request.use(
  (config) => {
    const ui = useUiStore();
    ui.startLoading();
    return config;
  },
  (error) => {
    const ui = useUiStore();
    ui.stopLoading();
    return Promise.reject(error);
  }
);

// Response interceptor
apiClient.interceptors.response.use(
  (response: AxiosResponse) => {
    const ui = useUiStore();
    ui.stopLoading();
    return response;
  },
  (error: AxiosError) => {
    const ui = useUiStore();
    const auth = useAuthStore();
    ui.stopLoading();

    if (!error.response) {
      // Network error
      ui.showToast('Chyba připojení k serveru', 'error');
      return Promise.reject(new ApiError('Network error', 0));
    }

    const { status, data } = error.response;

    switch (status) {
      case 401:
        // Unauthorized - redirect to login
        auth.logout();
        router.push('/login');
        break;

      case 403:
        // Forbidden
        ui.showToast('Nedostatečná oprávnění', 'error');
        break;

      case 404:
        // Not found
        ui.showToast('Záznam nenalezen', 'error');
        break;

      case 409:
        // Conflict - optimistic lock
        throw new OptimisticLockError(data);

      case 422:
        // Validation error
        throw new ValidationError(data);

      case 500:
        // Server error
        ui.showToast('Chyba serveru', 'error');
        break;
    }

    throw new ApiError(
      (data as any)?.detail || 'Unknown error',
      status,
      data
    );
  }
);
```

### 5.2 Parts API Module

```typescript
// src/api/parts.ts
import { apiClient } from './client';
import type { Part, PartCreate, PartUpdate, PartFull, PriceBreakdown } from '@/types';

export const partsApi = {
  // List parts with pagination
  async list(skip = 0, limit = 100): Promise<Part[]> {
    const { data } = await apiClient.get('/parts/', {
      params: { skip, limit }
    });
    return data;
  },

  // Search parts
  async search(query: string, skip = 0, limit = 100): Promise<{
    parts: Part[];
    total: number;
    skip: number;
    limit: number;
  }> {
    const { data } = await apiClient.get('/parts/search', {
      params: { search: query, skip, limit }
    });
    return data;
  },

  // Get single part
  async get(partNumber: string): Promise<Part> {
    const { data } = await apiClient.get(`/parts/${partNumber}`);
    return data;
  },

  // Get part with all relations
  async getFull(partNumber: string): Promise<PartFull> {
    const { data } = await apiClient.get(`/parts/${partNumber}/full`);
    return data;
  },

  // Create part
  async create(part: PartCreate): Promise<Part> {
    const { data } = await apiClient.post('/parts/', part);
    return data;
  },

  // Update part (optimistic locking)
  async update(partNumber: string, part: PartUpdate): Promise<Part> {
    const { data } = await apiClient.put(`/parts/${partNumber}`, part);
    return data;
  },

  // Delete part
  async delete(partNumber: string): Promise<void> {
    await apiClient.delete(`/parts/${partNumber}`);
  },

  // Duplicate part
  async duplicate(partNumber: string): Promise<Part> {
    const { data } = await apiClient.post(`/parts/${partNumber}/duplicate`);
    return data;
  },

  // Get pricing for quantity
  async getPricing(partNumber: string, quantity: number): Promise<PriceBreakdown> {
    const { data } = await apiClient.get(`/parts/${partNumber}/pricing`, {
      params: { quantity }
    });
    return data;
  },

  // Get pricing for multiple quantities
  async getPricingSeries(
    partNumber: string,
    quantities: number[]
  ): Promise<PriceBreakdown[]> {
    const { data } = await apiClient.get(`/parts/${partNumber}/pricing/series`, {
      params: { quantities: quantities.join(',') }
    });
    return data;
  },

  // Get stock (material) cost
  async getStockCost(partNumber: string): Promise<{ cost: number }> {
    const { data } = await apiClient.get(`/parts/${partNumber}/stock-cost`);
    return data;
  }
};
```

### 5.3 Other API Modules (Pattern)

```typescript
// src/api/operations.ts
import { apiClient } from './client';
import type { Operation, OperationCreate, OperationUpdate } from '@/types';

export const operationsApi = {
  async listByPart(partId: number): Promise<Operation[]> {
    const { data } = await apiClient.get(`/operations/part/${partId}`);
    return data;
  },

  async get(operationId: number): Promise<Operation> {
    const { data } = await apiClient.get(`/operations/${operationId}`);
    return data;
  },

  async create(operation: OperationCreate): Promise<Operation> {
    const { data } = await apiClient.post('/operations/', operation);
    return data;
  },

  async update(operationId: number, operation: OperationUpdate): Promise<Operation> {
    const { data } = await apiClient.put(`/operations/${operationId}`, operation);
    return data;
  },

  async delete(operationId: number): Promise<void> {
    await apiClient.delete(`/operations/${operationId}`);
  }
};

// Similar pattern for: batches, batchSets, workCenters, materials, admin
```

---

## 7. Store (Pinia) Design

### 6.1 Auth Store

```typescript
// src/stores/auth.ts
import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { authApi } from '@/api/auth';
import type { User, LoginRequest } from '@/types';

export const useAuthStore = defineStore('auth', () => {
  // State
  const user = ref<User | null>(null);
  const loading = ref(false);

  // Getters
  const isAuthenticated = computed(() => !!user.value);
  const isAdmin = computed(() => user.value?.role === 'admin');
  const isOperator = computed(() =>
    user.value?.role === 'admin' || user.value?.role === 'operator'
  );

  // Actions
  async function login(credentials: LoginRequest): Promise<void> {
    loading.value = true;
    try {
      const response = await authApi.login(credentials);
      user.value = response.user;
    } finally {
      loading.value = false;
    }
  }

  async function logout(): Promise<void> {
    await authApi.logout();
    user.value = null;
  }

  async function fetchCurrentUser(): Promise<void> {
    try {
      user.value = await authApi.me();
    } catch {
      user.value = null;
    }
  }

  return {
    // State
    user,
    loading,
    // Getters
    isAuthenticated,
    isAdmin,
    isOperator,
    // Actions
    login,
    logout,
    fetchCurrentUser
  };
});
```

### 6.2 Parts Store

```typescript
// src/stores/parts.ts
import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { partsApi } from '@/api/parts';
import type { Part, PartCreate, PartUpdate, PartFull } from '@/types';

export const usePartsStore = defineStore('parts', () => {
  // State
  const parts = ref<Part[]>([]);
  const currentPart = ref<PartFull | null>(null);
  const loading = ref(false);
  const searchQuery = ref('');
  const total = ref(0);

  // Getters
  const activeParts = computed(() =>
    parts.value.filter(p => !p.deleted_at)
  );

  const filteredParts = computed(() => {
    if (!searchQuery.value) return activeParts.value;
    const q = searchQuery.value.toLowerCase();
    return activeParts.value.filter(p =>
      p.part_number.toLowerCase().includes(q) ||
      p.name.toLowerCase().includes(q)
    );
  });

  // Actions
  async function fetchParts(skip = 0, limit = 100): Promise<void> {
    loading.value = true;
    try {
      parts.value = await partsApi.list(skip, limit);
    } finally {
      loading.value = false;
    }
  }

  async function searchParts(query: string): Promise<void> {
    loading.value = true;
    try {
      const result = await partsApi.search(query);
      parts.value = result.parts;
      total.value = result.total;
    } finally {
      loading.value = false;
    }
  }

  async function fetchPart(partNumber: string): Promise<void> {
    loading.value = true;
    try {
      currentPart.value = await partsApi.getFull(partNumber);
    } finally {
      loading.value = false;
    }
  }

  async function createPart(part: PartCreate): Promise<Part> {
    const newPart = await partsApi.create(part);
    parts.value.push(newPart);
    return newPart;
  }

  async function updatePart(partNumber: string, update: PartUpdate): Promise<Part> {
    const updated = await partsApi.update(partNumber, update);

    // Update in list
    const index = parts.value.findIndex(p => p.part_number === partNumber);
    if (index !== -1) {
      parts.value[index] = updated;
    }

    // Update current if same
    if (currentPart.value?.part_number === partNumber) {
      currentPart.value = { ...currentPart.value, ...updated };
    }

    return updated;
  }

  async function deletePart(partNumber: string): Promise<void> {
    await partsApi.delete(partNumber);
    parts.value = parts.value.filter(p => p.part_number !== partNumber);
  }

  function clearCurrentPart(): void {
    currentPart.value = null;
  }

  return {
    // State
    parts,
    currentPart,
    loading,
    searchQuery,
    total,
    // Getters
    activeParts,
    filteredParts,
    // Actions
    fetchParts,
    searchParts,
    fetchPart,
    createPart,
    updatePart,
    deletePart,
    clearCurrentPart
  };
});
```

### 6.3 Workspace Store

```typescript
// src/stores/workspace.ts
import { defineStore } from 'pinia';
import { ref, computed } from 'vue';

export type WorkspaceModule =
  | 'parts-list'
  | 'part-pricing'
  | 'part-operations'
  | 'part-material'
  | 'batch-sets';

export interface WorkspaceContext {
  partId: number | null;
  partNumber: string | null;
}

export const useWorkspaceStore = defineStore('workspace', () => {
  // State
  const activeModule = ref<WorkspaceModule>('parts-list');
  const context = ref<WorkspaceContext>({
    partId: null,
    partNumber: null
  });
  const recentParts = ref<Array<{ id: number; partNumber: string; name: string }>>([]);

  // Getters
  const hasPartContext = computed(() => !!context.value.partId);

  // Actions
  function setActiveModule(module: WorkspaceModule): void {
    activeModule.value = module;
  }

  function setPartContext(partId: number, partNumber: string, partName: string): void {
    context.value = { partId, partNumber };

    // Add to recent (max 10)
    const existing = recentParts.value.findIndex(p => p.id === partId);
    if (existing !== -1) {
      recentParts.value.splice(existing, 1);
    }
    recentParts.value.unshift({ id: partId, partNumber, name: partName });
    if (recentParts.value.length > 10) {
      recentParts.value.pop();
    }
  }

  function clearPartContext(): void {
    context.value = { partId: null, partNumber: null };
  }

  return {
    // State
    activeModule,
    context,
    recentParts,
    // Getters
    hasPartContext,
    // Actions
    setActiveModule,
    setPartContext,
    clearPartContext
  };
});
```

### 6.4 UI Store (Toasts, Loading)

```typescript
// src/stores/ui.ts
import { defineStore } from 'pinia';
import { ref } from 'vue';

export interface Toast {
  id: number;
  message: string;
  type: 'success' | 'error' | 'warning' | 'info';
  duration: number;
}

export const useUiStore = defineStore('ui', () => {
  // State
  const loading = ref(0); // Counter for concurrent requests
  const toasts = ref<Toast[]>([]);
  let toastId = 0;

  // Getters
  const isLoading = computed(() => loading.value > 0);

  // Actions
  function startLoading(): void {
    loading.value++;
  }

  function stopLoading(): void {
    loading.value = Math.max(0, loading.value - 1);
  }

  function showToast(
    message: string,
    type: Toast['type'] = 'info',
    duration = 3000
  ): void {
    const id = ++toastId;
    toasts.value.push({ id, message, type, duration });

    if (duration > 0) {
      setTimeout(() => removeToast(id), duration);
    }
  }

  function removeToast(id: number): void {
    const index = toasts.value.findIndex(t => t.id === id);
    if (index !== -1) {
      toasts.value.splice(index, 1);
    }
  }

  return {
    // State
    loading,
    toasts,
    // Getters
    isLoading,
    // Actions
    startLoading,
    stopLoading,
    showToast,
    removeToast
  };
});
```

---

## 8. Router Design

### 7.1 Route Definitions

```typescript
// src/router/index.ts
import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router';
import { useAuthStore } from '@/stores/auth';

// Lazy-loaded views
const LoginView = () => import('@/views/auth/LoginView.vue');
const DashboardView = () => import('@/views/dashboard/DashboardView.vue');
const PartsListView = () => import('@/views/parts/PartsListView.vue');
const PartCreateView = () => import('@/views/parts/PartCreateView.vue');
const PartEditView = () => import('@/views/parts/PartEditView.vue');
const PartPricingView = () => import('@/views/parts/PartPricingView.vue');
const WorkspaceView = () => import('@/views/workspace/WorkspaceView.vue');
const BatchSetsListView = () => import('@/views/pricing/BatchSetsListView.vue');
const BatchSetDetailView = () => import('@/views/pricing/BatchSetDetailView.vue');
const WorkCentersListView = () => import('@/views/workCenters/WorkCentersListView.vue');
const WorkCenterEditView = () => import('@/views/workCenters/WorkCenterEditView.vue');
const MasterDataView = () => import('@/views/admin/MasterDataView.vue');
const MaterialCatalogView = () => import('@/views/admin/MaterialCatalogView.vue');
const MaterialNormsView = () => import('@/views/admin/MaterialNormsView.vue');
const SettingsView = () => import('@/views/settings/SettingsView.vue');

const routes: RouteRecordRaw[] = [
  // Public routes
  {
    path: '/login',
    name: 'login',
    component: LoginView,
    meta: { public: true }
  },

  // Protected routes
  {
    path: '/',
    name: 'dashboard',
    component: DashboardView,
    meta: { title: 'Dashboard' }
  },

  // Parts
  {
    path: '/parts',
    name: 'parts-list',
    component: PartsListView,
    meta: { title: 'Seznam dílů' }
  },
  {
    path: '/parts/new',
    name: 'part-create',
    component: PartCreateView,
    meta: { title: 'Nový díl', requiresOperator: true }
  },
  {
    path: '/parts/:partNumber/edit',
    name: 'part-edit',
    component: PartEditView,
    meta: { title: 'Editace dílu' }
  },
  {
    path: '/parts/:partNumber/pricing',
    name: 'part-pricing',
    component: PartPricingView,
    meta: { title: 'Ceník dílu' }
  },

  // Workspace
  {
    path: '/workspace',
    name: 'workspace',
    component: WorkspaceView,
    meta: { title: 'Workspace' },
    children: [
      {
        path: 'parts',
        name: 'workspace-parts',
        component: () => import('@/views/workspace/modules/PartsListModule.vue')
      },
      {
        path: 'pricing',
        name: 'workspace-pricing',
        component: () => import('@/views/workspace/modules/PartPricingModule.vue')
      },
      {
        path: 'operations',
        name: 'workspace-operations',
        component: () => import('@/views/workspace/modules/PartOperationsModule.vue')
      },
      {
        path: 'materials',
        name: 'workspace-materials',
        component: () => import('@/views/workspace/modules/PartMaterialModule.vue')
      },
      {
        path: 'batch-sets',
        name: 'workspace-batch-sets',
        component: () => import('@/views/workspace/modules/BatchSetsModule.vue')
      }
    ]
  },

  // Pricing
  {
    path: '/pricing/batch-sets',
    name: 'batch-sets-list',
    component: BatchSetsListView,
    meta: { title: 'Cenové sady' }
  },
  {
    path: '/pricing/batch-sets/:id',
    name: 'batch-set-detail',
    component: BatchSetDetailView,
    meta: { title: 'Detail cenové sady' }
  },

  // Work Centers
  {
    path: '/work-centers',
    name: 'work-centers-list',
    component: WorkCentersListView,
    meta: { title: 'Pracovní centra' }
  },
  {
    path: '/work-centers/:number/edit',
    name: 'work-center-edit',
    component: WorkCenterEditView,
    meta: { title: 'Editace pracovního centra', requiresOperator: true }
  },

  // Admin
  {
    path: '/admin/master-data',
    name: 'master-data',
    component: MasterDataView,
    meta: { title: 'Master data', requiresAdmin: true }
  },
  {
    path: '/admin/materials',
    name: 'material-catalog',
    component: MaterialCatalogView,
    meta: { title: 'Katalog materiálů', requiresAdmin: true }
  },
  {
    path: '/admin/norms',
    name: 'material-norms',
    component: MaterialNormsView,
    meta: { title: 'Materiálové normy', requiresAdmin: true }
  },

  // Settings
  {
    path: '/settings',
    name: 'settings',
    component: SettingsView,
    meta: { title: 'Nastavení', requiresAdmin: true }
  },

  // Catch-all 404
  {
    path: '/:pathMatch(.*)*',
    redirect: '/'
  }
];

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) {
      return savedPosition;
    }
    return { top: 0 };
  }
});

// Navigation guards
router.beforeEach(async (to, from, next) => {
  const auth = useAuthStore();

  // Fetch user if not loaded
  if (!auth.user && !to.meta.public) {
    await auth.fetchCurrentUser();
  }

  // Check authentication
  if (!to.meta.public && !auth.isAuthenticated) {
    return next({ name: 'login', query: { redirect: to.fullPath } });
  }

  // Check admin access
  if (to.meta.requiresAdmin && !auth.isAdmin) {
    return next({ name: 'dashboard' });
  }

  // Check operator access
  if (to.meta.requiresOperator && !auth.isOperator) {
    return next({ name: 'dashboard' });
  }

  // Update document title
  if (to.meta.title) {
    document.title = `${to.meta.title} | GESTIMA`;
  }

  next();
});

export default router;
```

### 7.2 Route Meta Types

```typescript
// src/types/router.d.ts
import 'vue-router';

declare module 'vue-router' {
  interface RouteMeta {
    public?: boolean;
    title?: string;
    requiresAdmin?: boolean;
    requiresOperator?: boolean;
  }
}
```

---

## 9. Migration Phases

### Phase 1: Foundation + Backend Review (Week 1-2)

#### Day 1-2: Project Setup

```bash
# Create Vue project
cd /Users/lofas/Documents/__App_Claude/Gestima
npm create vue@latest frontend -- --template=vue-ts

# Navigate to frontend
cd frontend

# Install dependencies
npm install vue-router@4 pinia axios
npm install -D @types/node vite-plugin-vue-devtools

# Install form validation
npm install vee-validate @vee-validate/zod zod

# Install testing
npm install -D vitest @vue/test-utils jsdom
npm install -D @playwright/test

# Directory structure
mkdir -p src/{api,types,stores,composables,components/{layout,ui,forms,workspace},views/{auth,dashboard,parts,workspace/modules,pricing,workCenters,admin,settings}}
```

**Checklist Day 1-2:**
- [ ] Vue project created with TypeScript
- [ ] Vite configured with proxy to FastAPI
- [ ] Pinia, Vue Router, Axios installed
- [ ] Directory structure created
- [ ] CSS files copied from existing
- [ ] TypeScript strict mode enabled

#### Day 3-4: Core Infrastructure + Auth Router Review

**Vue files to create:**

1. `src/api/client.ts` - Axios instance with interceptors
2. `src/stores/auth.ts` - Authentication store
3. `src/stores/ui.ts` - UI state (toasts, loading)
4. `src/router/index.ts` - Basic routes
5. `src/App.vue` - Root component
6. `src/main.ts` - Vue app entry

**Backend review (auth_router.py):**

```
□ POST /api/auth/login - Review token handling
□ POST /api/auth/logout - Verify cookie clearing
□ GET /api/auth/me - Check response schema
□ Verify HttpOnly cookie security
□ Check password hashing (bcrypt)
□ Review session timeout
```

**Checklist Day 3-4:**
- [ ] API client with error handling
- [ ] Auth store with login/logout
- [ ] UI store with toasts
- [ ] Basic router setup
- [ ] App.vue with layout
- [ ] Login view working
- [ ] **auth_router.py reviewed & optimized**

#### Day 5-7: Layout & Auth + Parts Router Review

**Vue files to create:**

1. `src/components/layout/AppHeader.vue`
2. `src/components/layout/AppSidebar.vue`
3. `src/components/layout/AppFooter.vue`
4. `src/views/auth/LoginView.vue`
5. `src/components/ui/Toast.vue`
6. `src/components/ui/Spinner.vue`

**Backend review (parts_router.py):**

```
□ GET /api/parts/ - Pagination, eager loading
□ GET /api/parts/search - Query optimization
□ GET /api/parts/{part_number} - 404 handling
□ GET /api/parts/{part_number}/full - N+1 check
□ POST /api/parts/ - Input validation
□ PUT /api/parts/{part_number} - Optimistic lock
□ DELETE /api/parts/{part_number} - Soft delete
□ POST /api/parts/{part_number}/duplicate - Transaction
□ GET /api/parts/{part_number}/pricing - Calculation
□ GET /api/parts/{part_number}/stock-cost - Material cost
□ POST /api/parts/{part_number}/copy-material-geometry
□ GET /api/parts/{part_number}/pricing/series
□ Review Pydantic schemas (PartCreate, PartUpdate)
□ Check error messages consistency
```

**Checklist Day 5-7:**
- [ ] Header with user info, navigation
- [ ] Sidebar with menu items
- [ ] Footer with version
- [ ] Login form with validation
- [ ] Toast notifications working
- [ ] Loading spinner
- [ ] Protected route working
- [ ] **parts_router.py reviewed & optimized**
- [ ] **parts schemas reviewed**

### Phase 2: Workspace Migration + Services Review (Week 3-4)

#### Day 8-10: Workspace Shell

**Create files:**

1. `src/views/workspace/WorkspaceView.vue`
2. `src/components/workspace/WorkspaceTabs.vue`
3. `src/components/workspace/WorkspacePanel.vue`
4. `src/stores/workspace.ts`

**Functionality:**
- Tab navigation
- Module switching
- Part context (selected part)
- KeepAlive for module caching

**Checklist Day 8-10:**
- [ ] Workspace view with tabs
- [ ] Tab switching with transitions
- [ ] KeepAlive preserving state
- [ ] Workspace store managing context

#### Day 11-12: Parts List Module

**Migrate:** `app/static/js/modules/parts-list.js` → `PartsListModule.vue`

**Create files:**

1. `src/views/workspace/modules/PartsListModule.vue`
2. `src/stores/parts.ts`
3. `src/api/parts.ts`
4. `src/types/part.ts`

**Functionality:**
- Search parts (debounced)
- List with columns
- Select part (sets workspace context)
- Column visibility toggle

**Checklist Day 11-12:**
- [ ] Parts list rendering
- [ ] Search working
- [ ] Part selection updates context
- [ ] Pagination if needed

#### Day 13-14: Part Pricing Module + Batches Router Review

**Backend review (batches_router.py + pricing_router.py):**

```
□ GET /api/batches/part/{part_id} - Eager load batch_set
□ GET /api/batches/{batch_number} - 404 handling
□ POST /api/batches/ - Auto-calculate costs
□ DELETE /api/batches/{batch_number} - Soft delete check
□ POST /api/batches/{batch_number}/freeze - Transaction integrity
□ POST /api/batches/{batch_number}/clone - Deep copy
□ POST /api/batches/{batch_number}/recalculate - Frozen check
□ GET /api/pricing/batch-sets - List with counts
□ POST /api/pricing/batch-sets - Auto-generate number
□ POST /api/pricing/batch-sets/{id}/freeze - Atomic freeze all
□ Review price_calculator.py service
□ Check cost calculation accuracy
```

**Migrate:** `app/static/js/modules/part-pricing.js` → `PartPricingModule.vue`

**Create files:**

1. `src/views/workspace/modules/PartPricingModule.vue`
2. `src/stores/batches.ts`
3. `src/api/batches.ts`
4. `src/types/batch.ts`

**Functionality:**
- Display batches for selected part
- Price breakdown per quantity
- Create/delete batches
- Recalculate prices

**Checklist Day 13-14:**
- [ ] Batches list for part
- [ ] Price breakdown display
- [ ] Create batch working
- [ ] Delete batch working
- [ ] Recalculate working
- [ ] **batches_router.py reviewed & optimized**
- [ ] **pricing_router.py reviewed & optimized**
- [ ] **price_calculator.py reviewed**

#### Day 15-16: Part Operations Module + Operations Router Review

**Backend review (operations_router.py + features_router.py):**

```
□ GET /api/operations/part/{part_id} - Eager load work_center
□ POST /api/operations/ - Validate work_center exists
□ PUT /api/operations/{id} - Version check, time validation
□ DELETE /api/operations/{id} - Cascade features?
□ POST /api/operations/{id}/change-mode - Mode validation
□ GET /api/features/operation/{op_id} - Ordered by seq
□ POST /api/features/ - Sequence auto-assign
□ PUT /api/features/{id} - Time validation
□ DELETE /api/features/{id} - Recalculate parent
□ Review work center rate application
```

**Migrate:** `app/static/js/modules/part-operations.js` → `PartOperationsModule.vue`

**Create files:**

1. `src/views/workspace/modules/PartOperationsModule.vue`
2. `src/stores/operations.ts`
3. `src/api/operations.ts`
4. `src/types/operation.ts`

**Functionality:**
- List operations for part
- Inline editing (times, work center)
- Add/remove operations
- Reorder operations (drag?)

**Checklist Day 15-16:**
- [ ] Operations list
- [ ] Inline editing
- [ ] Add operation
- [ ] Delete operation
- [ ] Work center dropdown
- [ ] **operations_router.py reviewed & optimized**
- [ ] **features_router.py reviewed & optimized**

#### Day 17-18: Part Material Module + Materials Router Review

**Backend review (materials_router.py):**

```
□ GET /api/materials/groups - List all groups
□ GET /api/materials/items - Pagination, filtering
□ GET /api/materials/items/{number} - 404 handling
□ POST /api/materials/items - Auto-generate number
□ PUT /api/materials/items/{number} - Version check
□ DELETE /api/materials/items/{number} - Check references
□ POST /api/materials/parse - Parser accuracy
□ GET /api/materials/price-categories - Include tiers
□ GET /api/materials/price-tiers - Filtering
□ Review material_service.py
□ Check parser edge cases
```

**Migrate:** `app/static/js/modules/part-material.js` → `PartMaterialModule.vue`

**Create files:**

1. `src/views/workspace/modules/PartMaterialModule.vue`
2. `src/stores/materials.ts`
3. `src/api/materials.ts`
4. `src/types/material.ts`

**Functionality:**
- Material selection
- Stock type (bar, sheet, etc.)
- Dimensions (diameter, length)
- Material cost calculation

**Checklist Day 17-18:**
- [ ] Material dropdown
- [ ] Stock type selection
- [ ] Dimension inputs
- [ ] Cost display
- [ ] **materials_router.py reviewed & optimized**
- [ ] **material_service.py reviewed**

#### Day 19-21: Batch Sets Module + Work Centers Router Review

**Backend review (work_centers_router.py):**

```
□ GET /api/work-centers/ - Pagination
□ GET /api/work-centers/search - Multi-field search
□ GET /api/work-centers/types - Enum values
□ GET /api/work-centers/{number} - 404 handling
□ POST /api/work-centers/ - Rate validation
□ PUT /api/work-centers/{number} - Rate change detection
□ DELETE /api/work-centers/{number} - Check operation refs
□ POST /api/work-centers/{number}/recalculate-batches
□ Review hourly rate calculations
□ Check WorkCenter → Operation type mapping
```

**Migrate:** `app/static/js/modules/batch-sets.js` → `BatchSetsModule.vue`

**Create files:**

1. `src/views/workspace/modules/BatchSetsModule.vue`
2. `src/stores/batchSets.ts`
3. `src/api/batchSets.ts`
4. `src/types/batchSet.ts`

**Functionality:**
- List batch sets
- Create batch set
- Add batches to set
- Freeze/unfreeze set
- Clone set

**Checklist Day 19-21:**
- [ ] Batch sets list
- [ ] Create set
- [ ] Add batch to set
- [ ] Freeze set
- [ ] Clone set
- [ ] **work_centers_router.py reviewed & optimized**
- [ ] **All high-priority routers complete ✅**

### Phase 3: Remaining Pages + Admin/Config Review (Week 5-6)

#### Day 22-23: CRUD Pages (Parts)

**Create files:**

1. `src/views/parts/PartsListView.vue`
2. `src/views/parts/PartCreateView.vue`
3. `src/views/parts/PartEditView.vue`
4. `src/views/parts/PartPricingView.vue`

**Checklist Day 22-23:**
- [ ] Parts list page (full page view)
- [ ] Create part form
- [ ] Edit part form (tabs)
- [ ] Part pricing page

#### Day 24-25: Work Centers & Pricing Pages

**Create files:**

1. `src/views/workCenters/WorkCentersListView.vue`
2. `src/views/workCenters/WorkCenterEditView.vue`
3. `src/views/pricing/BatchSetsListView.vue`
4. `src/views/pricing/BatchSetDetailView.vue`

**Checklist Day 24-25:**
- [ ] Work centers list
- [ ] Work center edit form
- [ ] Batch sets list page
- [ ] Batch set detail page

#### Day 26-27: Admin Pages + Admin Router Review

**Backend review (admin_router.py + config_router.py):**

```
□ GET /api/admin/material-groups - Admin-only access
□ GET /api/admin/material-norms/search - Query optimization
□ POST /api/admin/material-norms - Duplicate check
□ PUT /api/admin/material-norms/{id} - Version check
□ DELETE /api/admin/material-norms/{id} - Soft delete
□ POST /api/admin/material-groups - Unique name
□ PUT /api/admin/material-groups/{id} - Version check
□ DELETE /api/admin/material-groups/{id} - Check item refs
□ POST /api/admin/material-price-categories - Validation
□ PUT /api/admin/material-price-categories/{id}
□ DELETE /api/admin/material-price-categories/{id}
□ GET /api/config/ - All config
□ PUT /api/config/{key} - Validate key exists
□ Review role-based access (Admin only)
```

**Create files:**

1. `src/views/admin/MasterDataView.vue`
2. `src/views/admin/MaterialCatalogView.vue`
3. `src/views/admin/MaterialNormsView.vue`

**Checklist Day 26-27:**
- [ ] Master data page
- [ ] Material catalog
- [ ] Material norms

#### Day 28: Dashboard & Settings

**Create files:**

1. `src/views/dashboard/DashboardView.vue`
2. `src/views/settings/SettingsView.vue`

**Checklist Day 28:**
- [ ] Dashboard with stats
- [ ] Settings page

### Phase 4: Testing & Deployment (Week 7-8)

#### Day 29-32: Testing

**Unit Tests:**
- Stores (Pinia)
- Composables
- API modules

**Component Tests:**
- Form components
- Data tables
- Modals

**E2E Tests (Playwright):**
- Login flow
- Create part flow
- Workspace navigation
- Batch pricing flow

**Checklist Day 29-32:**
- [ ] Unit tests passing (>80% coverage)
- [ ] Component tests passing
- [ ] E2E tests passing
- [ ] Performance tests (<100ms)

#### Day 33-35: Production Build & Integration

**Tasks:**
1. Production build optimization
2. FastAPI integration (serve Vue build)
3. Environment variables
4. Error tracking setup

**Update `app/main.py`:**

```python
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

# Serve Vue static assets
if os.path.exists("frontend/dist"):
    app.mount("/assets", StaticFiles(directory="frontend/dist/assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # Serve API routes normally
        if full_path.startswith("api/"):
            raise HTTPException(404)
        # Serve Vue SPA
        return FileResponse("frontend/dist/index.html")
```

**Checklist Day 33-35:**
- [ ] Production build working
- [ ] FastAPI serving Vue
- [ ] Environment variables configured
- [ ] Deployment tested

#### Day 36-40: Gradual Rollout

**Strategy:**
1. Deploy to staging
2. Internal testing (1 week)
3. Feature flag for Vue vs Jinja2
4. Gradual user migration
5. Monitor performance
6. Full switch

**Checklist Day 36-40:**
- [ ] Staging deployment
- [ ] Internal testing complete
- [ ] Production deployment
- [ ] Monitoring active
- [ ] Rollback plan tested

---

## 10. Performance Requirements

### 9.1 Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| Workspace tab switch | <50ms | Vue DevTools |
| Input → UI update | <16ms | Performance API |
| Page navigation | <50ms | Vue DevTools |
| Initial load (cold) | <500ms | Lighthouse |
| Initial load (warm) | <100ms | Lighthouse |
| Bundle size (gzip) | <100KB | Vite build |
| Memory footprint | <50MB | Chrome DevTools |
| Lighthouse score | >95 | Lighthouse |

### 9.2 Optimization Strategies

#### Code Splitting

```typescript
// Lazy load routes
const PartEditView = () => import('@/views/parts/PartEditView.vue');
```

#### Component Caching

```vue
<!-- Workspace keeps modules alive -->
<KeepAlive :max="5">
  <RouterView />
</KeepAlive>
```

#### Debounced Search

```typescript
// Composable for debounced values
const debouncedSearch = useDebouncedRef(searchQuery, 300);

watch(debouncedSearch, (value) => {
  store.searchParts(value);
});
```

#### Virtual Scrolling (if needed)

```vue
<!-- For large lists -->
<VirtualScroller :items="parts" :item-height="48">
  <template #default="{ item }">
    <PartRow :part="item" />
  </template>
</VirtualScroller>
```

---

## 11. Testing Strategy

### 10.1 Unit Tests (Vitest)

```typescript
// src/stores/__tests__/parts.spec.ts
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { setActivePinia, createPinia } from 'pinia';
import { usePartsStore } from '../parts';
import { partsApi } from '@/api/parts';

vi.mock('@/api/parts');

describe('Parts Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  it('fetches parts', async () => {
    const mockParts = [{ id: 1, part_number: '10000001', name: 'Test' }];
    vi.mocked(partsApi.list).mockResolvedValue(mockParts);

    const store = usePartsStore();
    await store.fetchParts();

    expect(store.parts).toEqual(mockParts);
    expect(store.loading).toBe(false);
  });

  it('handles fetch error', async () => {
    vi.mocked(partsApi.list).mockRejectedValue(new Error('Network error'));

    const store = usePartsStore();
    await expect(store.fetchParts()).rejects.toThrow();
  });
});
```

### 10.2 Component Tests

```typescript
// src/components/__tests__/Input.spec.ts
import { describe, it, expect } from 'vitest';
import { mount } from '@vue/test-utils';
import Input from '../ui/Input.vue';

describe('Input', () => {
  it('renders with label', () => {
    const wrapper = mount(Input, {
      props: { label: 'Username', modelValue: '' }
    });
    expect(wrapper.find('label').text()).toBe('Username');
  });

  it('emits update on input', async () => {
    const wrapper = mount(Input, {
      props: { modelValue: '' }
    });
    await wrapper.find('input').setValue('test');
    expect(wrapper.emitted('update:modelValue')).toEqual([['test']]);
  });
});
```

### 10.3 E2E Tests (Playwright)

```typescript
// e2e/login.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Login', () => {
  test('successful login redirects to dashboard', async ({ page }) => {
    await page.goto('/login');

    await page.fill('[data-testid="username"]', 'admin');
    await page.fill('[data-testid="password"]', 'admin123');
    await page.click('[data-testid="login-button"]');

    await expect(page).toHaveURL('/');
    await expect(page.locator('[data-testid="user-menu"]')).toBeVisible();
  });

  test('invalid credentials show error', async ({ page }) => {
    await page.goto('/login');

    await page.fill('[data-testid="username"]', 'wrong');
    await page.fill('[data-testid="password"]', 'wrong');
    await page.click('[data-testid="login-button"]');

    await expect(page.locator('[data-testid="error-message"]')).toBeVisible();
  });
});
```

### 10.4 Performance Tests

```typescript
// e2e/performance.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Performance', () => {
  test('workspace tab switch < 100ms', async ({ page }) => {
    await page.goto('/workspace');

    const start = performance.now();
    await page.click('[data-testid="tab-pricing"]');
    await page.waitForSelector('[data-testid="pricing-module"]');
    const end = performance.now();

    expect(end - start).toBeLessThan(100);
  });
});
```

---

## 12. Deployment Strategy

### 11.1 Development

```bash
# Terminal 1: FastAPI backend
cd /Users/lofas/Documents/__App_Claude/Gestima
python gestima.py run

# Terminal 2: Vue dev server
cd frontend
npm run dev

# Access: http://localhost:5173
# API proxied to: http://localhost:8000
```

### 11.2 Vite Config

```typescript
// frontend/vite.config.ts
import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import { resolve } from 'path';

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['vue', 'vue-router', 'pinia', 'axios']
        }
      }
    }
  }
});
```

### 11.3 Production Build

```bash
# Build Vue
cd frontend
npm run build

# Output: frontend/dist/
#   ├── index.html
#   └── assets/
#       ├── index-xxxxx.js
#       ├── index-xxxxx.css
#       └── vendor-xxxxx.js
```

### 11.4 FastAPI Integration

```python
# app/main.py
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

app = FastAPI(title="GESTIMA")

# Include API routers
app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(parts_router, prefix="/api", tags=["parts"])
# ... other routers

# Serve Vue SPA in production
VUE_DIST = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")

if os.path.exists(VUE_DIST):
    # Serve static assets
    app.mount("/assets", StaticFiles(directory=os.path.join(VUE_DIST, "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_vue_spa(full_path: str):
        """Serve Vue SPA for all non-API routes"""
        if full_path.startswith("api"):
            raise HTTPException(status_code=404, detail="API endpoint not found")

        index_path = os.path.join(VUE_DIST, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        raise HTTPException(status_code=404)
```

### 11.5 Single Command Run

```bash
# Run everything
python gestima.py run

# What it does:
# 1. Check if frontend/dist exists
# 2. If development: npm run dev in background
# 3. Start FastAPI server
# 4. Serve Vue SPA from /
```

---

## 13. Rollback Plan

### 12.1 Feature Flag

```python
# app/config.py
USE_VUE_SPA = os.getenv("USE_VUE_SPA", "false").lower() == "true"

# app/main.py
if USE_VUE_SPA and os.path.exists(VUE_DIST):
    # Serve Vue SPA
    ...
else:
    # Serve Jinja2 templates
    app.include_router(pages_router)
```

### 12.2 Rollback Steps

1. **Immediate (< 1 minute):**
   ```bash
   export USE_VUE_SPA=false
   python gestima.py run
   ```

2. **If issues discovered:**
   - Revert to Jinja2 templates
   - Investigate issue
   - Fix in Vue
   - Redeploy

3. **Keep Jinja2 templates during migration:**
   - Don't delete `app/templates/` until fully migrated
   - Both systems can coexist

### 12.3 Monitoring

**What to monitor:**
- Error rates (API, frontend)
- Response times
- User feedback
- Performance metrics

**Alerts:**
- Error rate > 1%
- Response time > 500ms
- Memory usage > 100MB

---

## Appendix A: Type Definitions

```typescript
// src/types/part.ts
export interface Part {
  id: number;
  part_number: string;
  name: string;
  article_number?: string;
  material_item_id?: number;
  stock_type: 'bar' | 'sheet' | 'profile' | 'custom';
  diameter?: number;
  length?: number;
  width?: number;
  height?: number;
  weight?: number;
  version: number;
  created_at: string;
  created_by?: number;
  updated_at?: string;
  updated_by?: number;
  deleted_at?: string;
}

export interface PartCreate {
  name: string;
  article_number?: string;
  material_item_id?: number;
  stock_type?: 'bar' | 'sheet' | 'profile' | 'custom';
  diameter?: number;
  length?: number;
}

export interface PartUpdate extends Partial<PartCreate> {
  version: number;
}

export interface PartFull extends Part {
  material_item?: MaterialItem;
  operations?: Operation[];
  batches?: Batch[];
}
```

```typescript
// src/types/operation.ts
export interface Operation {
  id: number;
  part_id: number;
  work_center_id?: number;
  seq: number;
  name: string;
  type: string;
  icon: string;
  setup_time_min: number;
  operation_time_min: number;
  version: number;
}

export interface OperationCreate {
  part_id: number;
  work_center_id?: number;
  name?: string;
  setup_time_min?: number;
  operation_time_min?: number;
}

export interface OperationUpdate extends Partial<OperationCreate> {
  version: number;
}
```

```typescript
// src/types/batch.ts
export interface Batch {
  id: number;
  batch_number: string;
  part_id: number;
  batch_set_id?: number;
  quantity: number;
  is_frozen: boolean;
  frozen_at?: string;
  stock_cost: number;
  machine_cost: number;
  overhead_cost: number;
  margin_cost: number;
  cooperation_cost: number;
  total_cost: number;
  unit_price: number;
  version: number;
}

export interface BatchSet {
  id: number;
  batch_set_number: string;
  part_id: number;
  name: string;
  is_frozen: boolean;
  frozen_at?: string;
  version: number;
  batches?: Batch[];
}
```

---

## Appendix B: Commands Reference

```bash
# Development
cd frontend
npm run dev          # Start Vite dev server
npm run build        # Production build
npm run preview      # Preview production build
npm run lint         # Run ESLint
npm run type-check   # Run TypeScript check
npm run test         # Run Vitest
npm run test:e2e     # Run Playwright

# Full app
cd /Users/lofas/Documents/__App_Claude/Gestima
python gestima.py run              # Run backend + frontend
python gestima.py run --dev        # Run with hot reload
python gestima.py run --build      # Build frontend first
```

---

## Appendix C: File Counts Summary

### Current (Alpine.js)

| Category | Files | LOC |
|----------|-------|-----|
| Templates | 19 | 9,382 |
| JavaScript | 13 | 4,133 |
| CSS | 7 | ~500 |
| **TOTAL** | **39** | **~14,000** |

### After Migration (Vue)

| Category | Files | LOC (est.) |
|----------|-------|------------|
| Vue Components | ~50 | ~8,000 |
| TypeScript (types, stores, api) | ~25 | ~2,500 |
| CSS (reused) | 7 | ~500 |
| **TOTAL** | **~82** | **~11,000** |

**Expected reduction:** ~21% less LOC, zero workarounds, full type safety.

---

**Document End**

*Generated: 2026-01-29*
*Author: Roy (AI Dev Team)*
*Status: Ready for implementation*
