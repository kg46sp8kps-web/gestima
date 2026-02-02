# Data TestID Checklist

## Why data-testid?

E2E tests require stable selectors that don't break when CSS changes. `data-testid` attributes provide:
- Stable selectors for Playwright tests
- Clear intent (this element is for testing)
- No coupling to CSS classes or IDs

## Naming Convention

```
data-testid="{component}-{element}-{type}"
```

Examples:
- `username-input` (input field)
- `login-button` (button)
- `parts-table` (table)
- `part-row` (table row)
- `toast` (notification)

## Files to Update

### ✅ Priority 1: E2E Critical Paths

#### Login Flow
- [ ] `src/views/auth/LoginView.vue`
  - [ ] `username-input`
  - [ ] `password-input`
  - [ ] `login-button`

#### Layout (always visible)
- [ ] `src/components/layout/AppHeader.vue`
  - [ ] `user-menu`
  - [ ] `user-menu-button`
  - [ ] `logout-button`

#### Parts Views
- [ ] `src/views/parts/PartsListView.vue`
  - [ ] `create-part-button`
  - [ ] `search-input`
  - [ ] `parts-table`

- [ ] `src/views/parts/PartCreateView.vue`
  - [ ] `part-name-input`
  - [ ] `part-description-input`
  - [ ] `save-button`
  - [ ] `cancel-button`

- [ ] `src/views/parts/PartDetailView.vue`
  - [ ] `part-name`
  - [ ] `tab-basic`
  - [ ] `tab-material`
  - [ ] `tab-operations`
  - [ ] `tab-pricing`

#### Workspace
- [ ] `src/views/workspace/WorkspaceView.vue`
  - [ ] `workspace-container`
  - [ ] `workspace-panel-1`
  - [ ] `workspace-panel-2`
  - [ ] `layout-picker-button`
  - [ ] `layout-option-{name}`

- [ ] `src/views/workspace/modules/PartsListModule.vue`
  - [ ] `module-parts-list`
  - [ ] `parts-table`
  - [ ] `part-row`
  - [ ] `selected-part-name`

- [ ] `src/views/workspace/modules/PartPricingModule.vue`
  - [ ] `module-part-pricing`
  - [ ] `pricing-part-name`
  - [ ] `create-batch-button`
  - [ ] `batch-quantity-input`
  - [ ] `save-batch-button`
  - [ ] `batches-table`
  - [ ] `batch-row`
  - [ ] `batch-quantity`
  - [ ] `recalculate-button`
  - [ ] `delete-batch-button`
  - [ ] `cost-breakdown`
  - [ ] `material-cost`
  - [ ] `operation-cost`
  - [ ] `total-cost`
  - [ ] `cost-breakdown-chart`
  - [ ] `material-cost-bar`
  - [ ] `operation-cost-bar`

- [ ] `src/views/workspace/modules/PartOperationsModule.vue`
  - [ ] `module-part-operations`
  - [ ] `operations-part-name`

- [ ] `src/views/workspace/modules/PartMaterialModule.vue`
  - [ ] `module-part-material`
  - [ ] `material-part-name`

- [ ] `src/views/workspace/modules/BatchSetsModule.vue`
  - [ ] `module-tab-batch-sets`
  - [ ] `create-batch-set-button`
  - [ ] `batch-set-name-input`
  - [ ] `save-batch-set-button`
  - [ ] `batch-set-row`
  - [ ] `batch-set-name`
  - [ ] `freeze-batch-set-button`
  - [ ] `batch-set-status`
  - [ ] `add-batch-to-set-button`
  - [ ] `batch-select-option-{quantity}`
  - [ ] `confirm-add-batch-button`
  - [ ] `batch-in-set`
  - [ ] `batch-in-set-quantity`

#### Common Components
- [ ] `src/components/ui/Toast.vue`
  - [ ] `toast`

- [ ] `src/components/ui/Modal.vue`
  - [ ] `modal`
  - [ ] `modal-backdrop`
  - [ ] `modal-close-button`

- [ ] `src/components/ui/ConfirmDialog.vue`
  - [ ] `confirm-dialog`
  - [ ] `confirm-delete-button`
  - [ ] `confirm-freeze-button`
  - [ ] `cancel-button`

- [ ] Empty states
  - [ ] `empty-state`
  - [ ] `empty-batches`

### ⚠️ Priority 2: Nice to Have

- [ ] `src/views/pricing/BatchSetsListView.vue`
- [ ] `src/views/pricing/BatchSetDetailView.vue`
- [ ] `src/views/workCenters/WorkCentersListView.vue`
- [ ] `src/views/workCenters/WorkCenterEditView.vue`
- [ ] `src/views/admin/MaterialCatalogView.vue`
- [ ] `src/views/settings/SettingsView.vue`

## Implementation Pattern

### Example: LoginView

```vue
<template>
  <div class="login-view">
    <form @submit.prevent="handleLogin">
      <Input
        v-model="username"
        label="Uživatelské jméno"
        data-testid="username-input"
      />
      <Input
        v-model="password"
        type="password"
        label="Heslo"
        data-testid="password-input"
      />
      <Button
        type="submit"
        data-testid="login-button"
      >
        Přihlásit
      </Button>
    </form>
  </div>
</template>
```

### Example: List Items

```vue
<template>
  <table data-testid="parts-table">
    <tbody>
      <tr
        v-for="part in parts"
        :key="part.id"
        data-testid="part-row"
        @click="selectPart(part)"
      >
        <td data-testid="part-number">{{ part.part_number }}</td>
        <td data-testid="part-name">{{ part.name }}</td>
      </tr>
    </tbody>
  </table>
</template>
```

## Testing data-testid

After adding attributes, verify with:

```bash
# Run E2E tests
npm run test:e2e

# Run specific test
npx playwright test e2e/01-login.spec.ts
```

## Notes

- ✅ Use kebab-case for IDs
- ✅ Keep IDs semantic (describe WHAT, not HOW)
- ✅ Prefix with component name for uniqueness
- ❌ Don't use CSS classes as test selectors
- ❌ Don't use dynamic IDs (use static part + dynamic suffix)

## Progress Tracking

- [ ] Phase 1: Priority 1 (E2E critical paths)
- [ ] Phase 2: Priority 2 (remaining views)
- [ ] Phase 3: Run E2E tests and verify all pass
