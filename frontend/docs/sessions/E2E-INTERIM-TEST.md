# E2E Interim Test - Day 32

**Date:** 2026-01-29
**Strategy:** Run E2E tests with partial `data-testid` implementation
**Goal:** Let Playwright tell us exactly what's missing

---

## ✅ data-testid Implemented

### 1. Login Flow (COMPLETE)
- ✅ `src/views/auth/LoginView.vue`
  - `username-input`
  - `password-input`
  - `login-button`

### 2. App Layout (COMPLETE)
- ✅ `src/components/layout/AppHeader.vue`
  - `user-menu`
  - `logout-button`

### 3. Parts Views (COMPLETE)
- ✅ `src/views/parts/PartsListView.vue`
  - `create-part-button`

- ✅ `src/views/parts/PartCreateView.vue`
  - `part-name-input`
  - `part-description-input`
  - `save-button`
  - `cancel-button`
  - `error-name`

- ✅ `src/views/parts/PartDetailView.vue`
  - `part-name`
  - Tabs: `tab-basic`, `tab-material`, `tab-operations`, `tab-pricing`

### 4. Common UI (PARTIAL)
- ✅ `src/components/ui/ToastContainer.vue`
  - `toast`

---

## 🚧 data-testid MISSING (Expected Failures)

### Workspace Views
- ❌ `src/views/workspace/WorkspaceView.vue`
  - `workspace-container`
  - `workspace-panel-1`, `workspace-panel-2`
  - `layout-picker-button`
  - `layout-option-{name}`
  - `module-tab-{name}`

### Workspace Modules
- ❌ `src/views/workspace/modules/PartsListModule.vue`
  - `module-parts-list`
  - `parts-table`
  - `part-row`
  - `search-input`
  - `selected-part-name`

- ❌ `src/views/workspace/modules/PartPricingModule.vue`
  - `module-part-pricing`
  - `pricing-part-name`
  - `create-batch-button`
  - `batch-quantity-input`
  - `save-batch-button`
  - `batches-table`
  - `batch-row`
  - All pricing-specific elements

- ❌ `src/views/workspace/modules/PartOperationsModule.vue`
  - `module-part-operations`
  - `operations-part-name`

- ❌ `src/views/workspace/modules/PartMaterialModule.vue`
  - `module-part-material`
  - `material-part-name`

- ❌ `src/views/workspace/modules/BatchSetsModule.vue`
  - `module-tab-batch-sets`
  - All batch set elements

### Common UI
- ❌ `src/components/ui/Modal.vue`
  - `modal`
  - `modal-backdrop`
  - `modal-close-button`

- ❌ `src/components/ui/ConfirmDialog.vue`
  - `confirm-dialog`
  - `confirm-delete-button`
  - `confirm-freeze-button`

- ❌ Empty states
  - `empty-state`
  - `empty-batches`

---

## 🎯 Test Execution Plan

### Phase 1: Login Flow (NOW)
```bash
npx playwright test e2e/01-login.spec.ts --headed
```

**Expected:**
- ✅ Test 1: Display login page - **PASS**
- ✅ Test 2: Show error on invalid credentials - **PASS** (if toast works)
- ✅ Test 3: Successful login - **PASS**
- ✅ Test 4: Successful logout - **PASS**
- ✅ Test 5: Redirect to login when accessing protected route - **PASS**
- ❌ Test 6: Preserve redirect URL - **MAY FAIL** (router behavior)

### Phase 2: Create Part Flow (AFTER FIX)
```bash
npx playwright test e2e/02-create-part.spec.ts --headed
```

**Expected:**
- ✅ Navigate to create part page - **PASS**
- ✅ Show validation errors - **PASS**
- ✅ Create part successfully - **PASS**
- ❌ Navigate to detail view - **FAIL** (tabs missing testid)
- ✅ Cancel creation - **PASS**

### Phase 3: Workspace (WILL FAIL)
```bash
npx playwright test e2e/03-workspace-navigation.spec.ts --headed
```

**Expected:**
- ❌ All tests FAIL - Missing workspace data-testids

### Phase 4: Batch Pricing (WILL FAIL)
```bash
npx playwright test e2e/04-batch-pricing.spec.ts --headed
```

**Expected:**
- ❌ All tests FAIL - Missing pricing module data-testids

---

## 📝 Iteration Strategy

1. **Run login test** → Identify failures
2. **Fix missing testids** → Add only what's needed
3. **Run create part test** → Identify failures
4. **Fix missing testids** → Add only what's needed
5. **Repeat** until all critical paths pass
6. **Document** what workspace tests need

---

## 🚀 Next Steps

After login test completes:
1. Review failures
2. Add missing `data-testid` attributes
3. Re-run test
4. Move to create part flow
5. Document workspace requirements for later

---

## 📊 Success Criteria

**Minimum viable:**
- ✅ Login flow: 6/6 tests passing
- ✅ Create part flow: 5/5 tests passing
- 🚧 Workspace: Document requirements
- 🚧 Batch pricing: Document requirements

**Full success:**
- All 28 E2E tests passing
- All critical user flows verified
- Performance <100ms confirmed
