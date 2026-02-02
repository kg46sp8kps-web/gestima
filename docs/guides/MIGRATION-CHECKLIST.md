# Module Migration Checklist

**Version:** 1.0
**Date:** 2026-02-02
**Purpose:** Step-by-step checklist for migrating existing modules to CustomizableModule

---

## Pre-Migration

### Analysis

- [ ] **Read documentation**
  - [ ] [ADR-030: Universal Responsive Module Template](../ADR/030-universal-responsive-module-template.md)
  - [ ] [Customizable Module Implementation Guide](CUSTOMIZABLE-MODULE-GUIDE.md)

- [ ] **Analyze current module**
  - [ ] Count LOC: `wc -l ModuleName.vue`
  - [ ] Identify sections (header, content, actions, modals)
  - [ ] List widget candidates (self-contained UI sections)
  - [ ] Check for duplicate CSS (grep for common patterns)

- [ ] **Estimate effort**
  - [ ] Number of widgets to create: _____
  - [ ] Expected LOC reduction: _____ LOC → _____ LOC
  - [ ] Migration time estimate: _____ hours

### Preparation

- [ ] **Create git branch**
  ```bash
  git checkout -b feature/migrate-MODULE_NAME-to-widgets
  ```

- [ ] **Backup existing tests**
  ```bash
  cp tests/ModuleName.spec.ts tests/ModuleName.spec.ts.backup
  ```

---

## Widget Creation

### Step 1: Identify Widgets

List all widgets to create:

- [ ] Widget 1: _________________ (Type: info-card / action-bar / form / chart)
- [ ] Widget 2: _________________ (Type: _____________)
- [ ] Widget 3: _________________ (Type: _____________)
- [ ] Widget 4: _________________ (Type: _____________)

### Step 2: Create Widget Files

For each widget:

- [ ] **Create widget file**
  ```bash
  touch frontend/src/components/widgets/WidgetName.vue
  ```

- [ ] **Define widget interface**
  ```typescript
  interface Props {
    context?: {
      // Define context shape
    }
  }
  ```

- [ ] **Extract logic** from original module
  - [ ] Move template HTML
  - [ ] Move script logic (composables, refs, computed)
  - [ ] Move styles (scoped CSS)

- [ ] **Implement events**
  ```typescript
  const emit = defineEmits<{
    'action': [action: string, payload?: any]
  }>()
  ```

- [ ] **Test widget standalone**
  - [ ] Create `WidgetName.spec.ts`
  - [ ] Test with mock context
  - [ ] Verify events emitted correctly

### Step 3: Widget Checklist

For each widget, verify:

- [ ] **< 300 LOC** (L-036 compliance)
- [ ] **Uses design tokens** (no hardcoded colors/spacing)
- [ ] **Props-based** (receives data via `context` prop)
- [ ] **Event-based** (emits `action` events, not direct calls)
- [ ] **Responsive** (uses container queries if needed)
- [ ] **Accessible** (ARIA labels, keyboard navigation)
- [ ] **Documented** (JSDoc comments for props/events)

---

## Layout Configuration

### Step 4: Create Module Config

- [ ] **Create config file**
  ```bash
  touch frontend/src/config/layouts/module-name.ts
  ```

- [ ] **Define widget definitions**
  ```typescript
  export const moduleConfig: ModuleLayoutConfig = {
    moduleKey: 'module-name',
    cols: 4,              // Number of columns
    rowHeight: 80,        // Row height in px
    widgets: [
      // Widget definitions...
    ],
    defaultLayouts: {
      compact: [/* ... */],
      comfortable: [/* ... */]
    }
  }
  ```

- [ ] **For each widget, define:**
  - [ ] `id` (unique widget identifier)
  - [ ] `type` (info-card, action-bar, form, chart, table, empty)
  - [ ] `title` (display title)
  - [ ] `component` (component filename without .vue)
  - [ ] `minWidth`, `minHeight` (minimum grid size)
  - [ ] `defaultWidth`, `defaultHeight` (default grid size)
  - [ ] `resizable` (can user resize?)
  - [ ] `removable` (can user remove?)
  - [ ] `required` (must be visible?)

- [ ] **Define default layouts**
  - [ ] Compact mode layout (for compact density)
  - [ ] Comfortable mode layout (for comfortable density)

### Step 5: Layout Testing

- [ ] **Test compact layout**
  - [ ] All widgets fit (no overflow)
  - [ ] No overlapping widgets
  - [ ] Logical visual hierarchy

- [ ] **Test comfortable layout**
  - [ ] Widgets properly spaced
  - [ ] Uses available space efficiently
  - [ ] Comfortable padding/gaps

- [ ] **Test responsive**
  - [ ] Resize window to 768px (tablet)
  - [ ] Resize window to 1920px (desktop)
  - [ ] Resize window to 3440px (ultrawide)
  - [ ] Verify container queries work

---

## Module Migration

### Step 6: Update Module Component

- [ ] **Import CustomizableModule**
  ```typescript
  import CustomizableModule from '@/components/layout/CustomizableModule.vue'
  import { moduleConfig } from '@/config/layouts/module-name'
  ```

- [ ] **Create context computed**
  ```typescript
  const context = computed(() => ({
    // Data to pass to widgets
  }))
  ```

- [ ] **Implement widget action handler**
  ```typescript
  function handleWidgetAction(widgetId: string, action: string, payload?: any) {
    switch (action) {
      case 'action-name':
        // Handle action
        break
      default:
        console.warn('Unknown action:', action)
    }
  }
  ```

- [ ] **Replace template**
  ```vue
  <template>
    <CustomizableModule
      :config="moduleConfig"
      :context="context"
      @widget-action="handleWidgetAction"
    />
  </template>
  ```

- [ ] **Add left panel (if split-pane)**
  ```vue
  <CustomizableModule
    :config="moduleConfig"
    :context="context"
    :left-panel-component="ListPanel"
    :left-panel-collapsible="true"
    @widget-action="handleWidgetAction"
  />
  ```

### Step 7: Clean Up

- [ ] **Remove old code**
  - [ ] Delete extracted widget code from module
  - [ ] Remove duplicate CSS
  - [ ] Remove unused imports
  - [ ] Remove unused composables

- [ ] **Verify LOC reduction**
  ```bash
  wc -l ModuleName.vue
  # Should be < 100 LOC (target: 60-80% reduction)
  ```

---

## Testing

### Step 8: Unit Tests

- [ ] **Widget tests**
  - [ ] Test each widget with mock context
  - [ ] Test event emissions
  - [ ] Test edge cases (null data, loading states)

- [ ] **Module tests**
  - [ ] Test context passing
  - [ ] Test widget action handling
  - [ ] Test layout persistence (localStorage)

- [ ] **Run all tests**
  ```bash
  npm run test -- ModuleName.spec.ts
  ```

### Step 9: Integration Tests

- [ ] **Manual testing checklist**
  - [ ] Open module in browser
  - [ ] Verify default layout displays
  - [ ] Test all widget actions
  - [ ] Test drag & drop (if enabled)
  - [ ] Test resize (if enabled)
  - [ ] Test add widget (if enabled)
  - [ ] Test remove widget (if enabled)
  - [ ] Test reset layout
  - [ ] Close and reopen → layout persists

- [ ] **Responsive testing**
  - [ ] Resize window to 768px (tablet)
  - [ ] Resize window to 1920px (desktop)
  - [ ] Resize window to 3440px (ultrawide)
  - [ ] Verify no overflow
  - [ ] Verify no wasted space

- [ ] **Cross-browser testing**
  - [ ] Chrome (container queries support)
  - [ ] Firefox 110+ (container queries support)
  - [ ] Safari 16+ (container queries support)

### Step 10: Regression Testing

- [ ] **Compare with original**
  - [ ] All features work (no missing functionality)
  - [ ] No visual regressions
  - [ ] Performance same or better
  - [ ] No new console errors/warnings

- [ ] **Linking groups** (if applicable)
  - [ ] Test with linkingGroup prop
  - [ ] Verify context sharing works
  - [ ] Test window communication

---

## Code Quality

### Step 11: L-036 Compliance

- [ ] **Check LOC for all files**
  ```bash
  find frontend/src/components/widgets -name "*.vue" -exec wc -l {} +
  find frontend/src/components/modules -name "ModuleName.vue" -exec wc -l {} +
  ```

- [ ] **Verify all < 300 LOC**
  - [ ] Module: _____ LOC (target: < 100)
  - [ ] Widget 1: _____ LOC (target: < 300)
  - [ ] Widget 2: _____ LOC (target: < 300)
  - [ ] Widget 3: _____ LOC (target: < 300)

### Step 12: Design System Compliance

- [ ] **No hardcoded values**
  ```bash
  # Check for hardcoded colors
  grep -r "color: #" frontend/src/components/widgets/
  # Should return 0 results

  # Check for hardcoded spacing
  grep -r "padding: [0-9]" frontend/src/components/widgets/
  # Should return 0 results
  ```

- [ ] **All use design tokens**
  - [ ] Colors: `var(--color-*)`
  - [ ] Spacing: `var(--space-*)`
  - [ ] Typography: `var(--text-*)`
  - [ ] Borders: `var(--border-*)`
  - [ ] Shadows: `var(--shadow-*)`

### Step 13: TypeScript Types

- [ ] **No `any` types**
  ```bash
  grep -r ": any" frontend/src/components/widgets/
  # Fix all instances
  ```

- [ ] **Props interfaces defined**
- [ ] **Events interfaces defined**
- [ ] **Context shape documented**

---

## Documentation

### Step 14: Code Documentation

- [ ] **JSDoc comments**
  - [ ] Module component (purpose, props, events)
  - [ ] Each widget (purpose, context shape, actions)
  - [ ] Layout config (explain widget arrangement)

- [ ] **README update** (if applicable)
  - [ ] Add module to list of migrated modules
  - [ ] Document new widgets

### Step 15: Migration Notes

- [ ] **Document changes**
  - [ ] LOC before: _____ LOC
  - [ ] LOC after: _____ LOC
  - [ ] Reduction: _____ LOC (_____ %)
  - [ ] Widgets created: _____
  - [ ] Issues encountered: _____
  - [ ] Learnings: _____

---

## Deployment

### Step 16: Commit & Push

- [ ] **Review changes**
  ```bash
  git status
  git diff
  ```

- [ ] **Commit with message**
  ```bash
  git add .
  git commit -m "feat: migrate ModuleName to widget-based architecture

  - Created X widgets (WidgetA, WidgetB, WidgetC)
  - Reduced LOC: XXX → YY (ZZ% reduction)
  - Added container queries for responsive design
  - All tests passing

  Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
  ```

- [ ] **Push to remote**
  ```bash
  git push origin feature/migrate-MODULE_NAME-to-widgets
  ```

### Step 17: Code Review

- [ ] **Create PR**
  - [ ] Title: `feat: migrate ModuleName to widget-based architecture`
  - [ ] Description: Summarize changes, LOC reduction, testing done
  - [ ] Link to ADR-030
  - [ ] Screenshots (before/after)

- [ ] **Request review**
  - [ ] Assign reviewer
  - [ ] Add "refactoring" label
  - [ ] Add "no-breaking-changes" label

### Step 18: Merge & Deploy

- [ ] **Address review feedback**
- [ ] **Squash & merge**
- [ ] **Delete branch**
  ```bash
  git checkout main
  git pull
  git branch -d feature/migrate-MODULE_NAME-to-widgets
  ```

- [ ] **Verify in production**
  - [ ] Module loads correctly
  - [ ] Layout persists
  - [ ] No console errors

---

## Post-Migration

### Step 19: Monitoring

- [ ] **Monitor for issues**
  - [ ] Check error logs (first 24h)
  - [ ] User feedback (first week)
  - [ ] Performance metrics (Lighthouse)

- [ ] **Iterate if needed**
  - [ ] Fix bugs
  - [ ] Adjust default layouts
  - [ ] Add missing widgets

### Step 20: Knowledge Sharing

- [ ] **Team demo** (optional)
  - [ ] Show widget system
  - [ ] Demonstrate customization
  - [ ] Share learnings

- [ ] **Update documentation**
  - [ ] Add module to migration tracker
  - [ ] Document gotchas/tips
  - [ ] Update CHANGELOG

---

## Module-Specific Checklists

### PartDetailPanel

- [ ] Widgets:
  - [ ] PartInfoCard (part details)
  - [ ] PartActionsBar (Material, Operations, Pricing, Drawing buttons)
- [ ] Modals stay in module: DrawingsManagementModal, CopyPartModal
- [ ] Target LOC: 454 → < 100

### PricingDetailPanel (1,119 LOC → Split into tabs)

- [ ] Widgets:
  - [ ] BatchListWidget (batch management)
  - [ ] CostBreakdownWidget (cost calculation)
  - [ ] PricingSettingsWidget (pricing config)
- [ ] Consider tab-based layout (not grid)
- [ ] Target LOC: 1,119 → < 300 (3-4 widgets)

### MaterialDetailPanel (969 LOC)

- [ ] Widgets:
  - [ ] MaterialSummaryWidget (metrics)
  - [ ] MaterialFormWidget (input form)
  - [ ] MaterialHistoryWidget (list)
- [ ] Target LOC: 969 → < 300 (3 widgets)

---

## Success Criteria

Migration is successful when:

- ✅ All tests passing (no regressions)
- ✅ LOC reduced by 60-80%
- ✅ All widgets < 300 LOC (L-036)
- ✅ Zero CSS duplication
- ✅ Layout customizable (drag/resize works)
- ✅ Responsive (tablet to ultrawide)
- ✅ localStorage persistence works
- ✅ No console errors/warnings
- ✅ Documentation complete

---

**Last Updated:** 2026-02-02
**Version:** 1.0
**Status:** ✅ Production Ready
