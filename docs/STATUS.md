# GESTIMA - Current Status

**Last Updated:** 2026-01-29
**Version:** 1.10.1
**Status:** 🚀 ROAD TO BETA - Milestone 0 Complete! Navigation Fixed!

---

## 🧭 Latest: Milestone 0 - Navigation Fix ✅ COMPLETED (Day 32)

**Users can now navigate from ANYWHERE to ANYWHERE!**

### ✅ Completed
- ✅ **App.vue** - Global layout with conditional header/footer
- ✅ **AppHeader.vue** - Hamburger menu navigation
  - Logo: KOVO RYBKA red fish + GESTIMA (red/black) + version badge
  - Search icon (Ctrl+K) with dropdown
  - Favorites icon (placeholder)
  - User badge (username + role)
  - Hamburger dropdown: Dashboard, Díly, Sady cen, Pracoviště, Windows, Nastavení, Master Data (admin), Logout
- ✅ **AppFooter.vue** - 3-column layout
  - "Be lazy. It's way better than talking to people." motto
  - Original branding from Alpine.js era
- ✅ **WindowsView.vue** - Fixed to work within global chrome (header visible)

### Impact
- ❌ BEFORE: User TRAPPED after leaving Dashboard (no navigation)
- ✅ AFTER: Full navigation from anywhere to anywhere!

### Next: Milestone 1 - Core Flow
- PartOperationsModule.vue (WorkCenter dropdown, inline editing)
- PartMaterialModule.vue (MaterialInput API integration)
- PartPricingModule.vue (Batch pricing display)

---

## 🪟 Floating Windows System (v1.10.0 - Day 31)

**First complete Vue 3 feature - zero Alpine.js!**

### ✅ Completed
- ✅ **WindowsStore** - State management s Pinia
  - findFreePosition() - no overlapping
  - arrangeWindows() - Grid/Horizontal/Vertical
  - Save/Load views + localStorage
  - Favorite views support
- ✅ **FloatingWindow Component**
  - Drag & drop (titlebar)
  - Resize (bottom-right corner)
  - Collision detection - NESMÍ se překrývat
  - Magnetic snapping - 15px threshold
  - Screen boundaries - NEMOHOU opustit viewport
  - Minimize/Maximize/Close controls
- ✅ **WindowManager Component**
  - Toolbar s module buttons
  - Arrange dropdown (Grid/Horizontal/Vertical)
  - Save/Load views
  - Favorite views quick-access
  - Minimized windows bar
- ✅ **5 Module Placeholders** (ready pro integraci)
- ✅ **Route Update** - `/workspace` → `/windows`

### Technical Highlights
- **Collision Detection**: Rectangle overlap algorithm
- **Boundary Enforcement**: Math.max/min clamping (x=[0, screenW-winW], y=[100, screenH-winH])
- **Magnetic Snapping**: 15px threshold na všechny strany (funguje při drag i resize)
- **Auto-Arrange**: Když není místo → auto grid → add new → arrange all

### Impact
- ✅ **Vue Migration Milestone** - First complete Vue 3 + Pinia feature!
- ✅ Foundation for future SPA migration
- ✅ Reusable component architecture
- ✅ Zero overlapping, zero out-of-bounds bugs

**Notes:** Final Alpine.js release (v1.6.1). Windows system = test-bed pro budoucí full SPA migration. Viz: [docs/VUE-MIGRATION.md](VUE-MIGRATION.md)

---

## 🛡️ Mandatory Verification Protocol (v1.9.5 - Day 29)

**Trust Recovery: From chat agreement → Embedded in CLAUDE.md!**

### ✅ Completed
- ✅ CLAUDE.md Section 4: MANDATORY VERIFICATION checklist
  - Banned phrases ("mělo by být OK")
  - Required phrases ("Verification: grep = 0 matches")
  - Verification protocol for Frontend CSS, Backend, Multi-file refactor
- ✅ CLAUDE.md WORKFLOW: Systematic approach for multi-file changes
  - grep ALL → read ALL → edit ALL → verify
  - Porušení = opakování 4x → ztráta důvěry!
- ✅ KRITICKÁ PRAVIDLA #13: MANDATORY VERIFICATION
- ✅ ANTI-PATTERNS.md: L-033, L-034, L-035 with incident analysis
  - L-035 CRITICAL: 4-attempt incident breakdown
  - Root cause, impact, prevention checklist

**Impact:** No more "should be OK" without grep proof! Self-correcting workflow embedded in AI logic.

---

## 🎨 Design System Cleanup (v1.9.4 - Day 29)

**ONE Building Block principle enforced!**

### ✅ Completed
- ✅ Removed ALL duplicate CSS utility classes (372 lines!)
  - `.btn*`, `.part-badge`, `.time-badge*`, `.frozen-badge` variants
  - 5 workspace modules cleaned (213 lines)
  - 6 view components cleaned (159 lines)
- ✅ Single source of truth: `design-system.css` ONLY
- ✅ Verified: Zero duplicate definitions remain (grep confirmed)
- ✅ Consistent badge/button styling across ENTIRE app
- ✅ Documentation updated: CHANGELOG + CLAUDE.md (L-033, L-034, L-035)

**Impact:** Consistent UX, easier maintenance, smaller bundle, zero visual regressions!

---

## 🎉 Latest: Vue SPA Testing Complete (Phase 4 - Day 29-31)

**Breaking Change:** Material moved from Part to MaterialInput (Lean Part architecture)

### ✅ Completed
- ✅ DB Schema - `material_inputs` + `material_operation_link` tables
- ✅ Models - MaterialInput, Part (revision fields), Operation (M:N)
- ✅ Migration - Alembic `a8b9c0d1e2f3` applied
- ✅ API - 8 new endpoints (CRUD + link/unlink)
- ✅ Price Calculator - New functions for MaterialInput
- ✅ Documentation - ADR-024 + CHANGELOG v1.8.0

### 🚧 Pending
- 🚧 Frontend - PartMaterialModule.vue (MaterialInput API)
- 🚧 Frontend - PartOperationsModule.vue (display linked materials)
- 🚧 Tests - Backend pytest for new endpoints

**Benefits:** Part is now lean (identity only), supports 1-N materials, M:N material-operation relationships, BOM-ready for v3.0 PLM.

---

## 🎯 Current Focus

**Phase 4: Testing & Deployment (Week 7-8)**
- ✅ Unit tests (Vitest) - **286 tests passing!**
- ✅ Store tests (auth, ui, parts, operations)
- ✅ API tests (client, interceptors, errors)
- ✅ Component tests (Button, Input, Modal, DataTable, FormTabs, Spinner, Select)
- 🚧 E2E tests (Playwright)
- 🚧 Performance optimization
- 🚧 FastAPI integration
- 🚧 Deployment strategy

---

## 📊 Vue SPA Migration Progress

| Phase | Status | Progress | Duration |
|-------|--------|----------|----------|
| Phase 1: Foundation | ✅ Complete | 100% | 7 days (Day 1-7) |
| Phase 2: Workspace | ✅ Complete | 100% | 14 days (Day 8-21) |
| Phase 3: Remaining Pages | ✅ Complete | 100% | 7 days (Day 22-28) |
| **Phase 4: Testing & Deployment** | ⏳ In Progress | 25% | 12 days (Day 29-40) |

**Overall Progress:** 75% (28/40 days)

---

## ✅ Phase 4 - Testing (Day 29-31)

### 🎯 Test Coverage: 286 tests passing

| Category | Tests | Files | Coverage |
|----------|-------|-------|----------|
| **Stores** | 87 | 4 | auth, ui, parts, operations |
| **API** | 20 | 1 | client, interceptors, errors |
| **Components** | 178 | 7 | Button, Input, Modal, DataTable, FormTabs, Spinner, Select |
| **Demo** | 1 | 1 | HelloWorld |
| **TOTAL** | **286** | **13** | **100% pass rate** |

### Technical Highlights
- ✅ **Vitest 4.0.18** - Fast, modern testing framework
- ✅ **@vue/test-utils** - Vue component testing
- ✅ **Pinia testing** - Store unit tests with mocked API
- ✅ **axios-mock-adapter** - HTTP request mocking
- ✅ **Teleport testing** - Modal component with document.querySelector
- ✅ **Deep equality** - Object comparison with toEqual()
- ✅ **Intl.NumberFormat** - Non-breaking space handling

### Lessons Learned (L-024 to L-027)
- **L-024:** Teleport requires `document.querySelector` + `attachTo: document.body`
- **L-025:** `textContent` includes whitespace - use `.trim()` when needed
- **L-026:** Deep object equality requires `.toEqual()`, not `.toContain()`
- **L-027:** `Intl.NumberFormat` uses non-breaking spaces - `.replace(/\u00A0/g, ' ')`

### Build Time
- Test execution: **~1.2s** for 286 tests
- Bundle size: **60.67 KB gzipped** (unchanged)

---

## ✅ Phase 3 Completed (Day 22-28)

### Shared Components (2)
- ✅ DataTable.vue - Universal table
- ✅ FormTabs.vue - Tab layout

### Views Created (9)
- ✅ PartsListView
- ✅ PartCreateView
- ✅ PartDetailView (4 tabs with inline modules) ⭐
- ✅ WorkCentersListView
- ✅ WorkCenterEditView
- ✅ BatchSetsListView
- ✅ MasterDataView (admin)
- ✅ SettingsView
- ✅ WindowsView (floating windows) ⭐ NEW

### Routes Added (10)
- ✅ `/parts` - Parts list
- ✅ `/parts/new` - Create part
- ✅ `/parts/:partNumber` - Part detail
- ✅ `/work-centers` - Work centers list
- ✅ `/work-centers/new` - Create work center
- ✅ `/work-centers/:workCenterNumber` - Edit work center
- ✅ `/pricing/batch-sets` - Batch sets list
- ✅ `/admin/master-data` - Admin master data
- ✅ `/settings` - Settings
- ✅ `/windows` - Floating windows (NEW)

### Backend Reviewed (3 routers, 32 endpoints)
- ✅ materials_router.py (15 endpoints)
- ✅ work_centers_router.py (7 endpoints)
- ✅ admin_router.py (10 endpoints)

### Build Metrics
- Bundle size: **60.67 KB gzipped** ✅ (under 100KB target)
- Build time: 1.66s
- TypeScript: Strict mode passing ✅

---

## 📦 System Architecture

### Frontend (Vue 3 + TypeScript)
```
src/
├── views/
│   ├── auth/ (1 view) - Login
│   ├── dashboard/ (1 view) - Dashboard
│   ├── parts/ (3 views) - List, Create, Detail
│   ├── workCenters/ (2 views) - List, Edit
│   ├── pricing/ (1 view) - BatchSets List
│   ├── workspace/ (1 view + 5 modules)
│   ├── windows/ (1 view) - Floating Windows ⭐ NEW
│   ├── admin/ (1 view) - MasterData
│   └── settings/ (1 view) - Settings
├── components/
│   ├── ui/ (8 components) - DataTable, FormTabs, Modal, etc.
│   ├── layout/ (2 components) - AppHeader, AppFooter
│   ├── workspace/ (2 components) - Panel, Toolbar
│   ├── windows/ (2 components) - FloatingWindow, WindowManager ⭐ NEW
│   └── modules/ (5 components) - Parts, Pricing, Operations, Material, BatchSets ⭐ NEW
├── stores/ (7 stores) - auth, ui, parts, batches, operations, materials, windows ⭐ NEW
├── api/ (5 modules) - parts, batches, operations, materials, auth
└── router/ - 19 routes with guards (1 new: /windows) ⭐ NEW

Total: 13 views, 19 routes, 7 stores, 17+ components
```

### Backend (FastAPI + SQLAlchemy)
- ✅ All routers reviewed (parts, batches, operations, features, materials, work_centers, admin)
- ✅ Optimistic locking (ADR-008)
- ✅ Role-based access
- ✅ Soft delete pattern

---

## 🚀 What's Working

### ✅ Fully Functional
- Authentication & Authorization (login, role-based access)
- Parts management (list, create, detail with 4 tabs)
- Workspace (multi-panel, tab switching, part selection)
- Operations module (inline editing, add/delete, work centers)
- Material module (parser, stock cost calculation)
- Pricing module (batches, sets, cost breakdown)
- Work Centers (list, create/edit)
- Settings (user preferences)
- **Floating Windows** (drag, resize, snap, save/load views) ⭐ NEW
- DataTable component (sorting, pagination, formatting)
- FormTabs component (horizontal/vertical, badges)

### ⏳ Placeholder/TODO
- Admin master data (placeholder, needs implementation)
- Batch set detail view (route exists, view TODO)
- Part pricing standalone view (route TODO)

---

## 📝 Next Steps (Phase 4)

### Week 7: Testing
1. **Unit Tests (Vitest)**
   - Stores (auth, parts, operations, batches, materials, ui)
   - API modules (interceptors, error handling)
   - Utilities/helpers
   - Target: >80% coverage

2. **Component Tests**
   - DataTable (sorting, pagination, selection)
   - FormTabs (tab switching, disabled states)
   - Modal, ConfirmDialog
   - Form components (Input, Select, etc.)

3. **E2E Tests (Playwright)**
   - Login flow
   - Create part → Add material → Add operations → View pricing
   - Workspace navigation
   - Batch pricing workflow
   - Work center CRUD

4. **Performance Tests**
   - Lighthouse audit (target: >95)
   - Tab switch <50ms
   - Input update <16ms
   - Memory <50MB

### Week 8: Deployment
1. **Production Build**
   - Environment variables
   - Build optimization
   - Code splitting

2. **FastAPI Integration**
   - Serve Vue from FastAPI
   - SPA routing (catch-all)
   - Static assets

3. **Deployment Strategy**
   - Staging deployment
   - Internal testing (1 week)
   - Feature flag (Vue vs Jinja2)
   - Gradual rollout
   - Monitoring & rollback plan

---

## 📊 Quality Metrics

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| Bundle size | <100KB gzip | 60.67 KB | ✅ |
| Build time | <5s | 1.66s | ✅ |
| TypeScript | Strict | Passing | ✅ |
| Test coverage | >80% | 0% | ⏳ |
| Lighthouse | >95 | TBD | ⏳ |
| Tab switch | <50ms | TBD | ⏳ |

---

## 🐛 Known Issues

None. All TypeScript errors resolved, build passing.

---

## 📚 Documentation

- ✅ [VUE-MIGRATION.md](VUE-MIGRATION.md) - Complete migration guide
- ✅ [CHANGELOG.md](../CHANGELOG.md) - Version history
- ✅ [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture
- ✅ [UI-GUIDE.md](UI-GUIDE.md) - UI patterns and components
- ✅ [CLAUDE.md](../CLAUDE.md) - AI assistant rules

---

**Status Summary:** Phase 3 complete + Floating Windows System implemented (v1.10.0). 13 views, 19 routes, 7 stores, 17+ components. First complete Vue 3 feature (zero Alpine.js). Bundle size 60.67 KB gzipped. Ready for Phase 4: Testing & Deployment. 🚀
