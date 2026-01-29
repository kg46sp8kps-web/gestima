# E2E Tests (Playwright)

## Overview

End-to-End tests for GESTIMA Vue SPA using Playwright.

## Structure

```
e2e/
├── helpers/
│   ├── auth.ts         # Login/logout helpers
│   └── test-data.ts    # Test data generators
├── 01-login.spec.ts    # Login/logout flow
├── 02-create-part.spec.ts  # Part creation flow
├── 03-workspace-navigation.spec.ts  # Workspace module switching
└── 04-batch-pricing.spec.ts  # Batch pricing flow
```

## Running Tests

### Local Development (headful)

```bash
# Run all tests
npm run test:e2e

# Run specific test file
npx playwright test e2e/01-login.spec.ts

# Run in UI mode (interactive)
npx playwright test --ui

# Run in headed mode (see browser)
npx playwright test --headed

# Debug mode
npx playwright test --debug
```

### CI (headless)

```bash
# Runs automatically in CI with preview build
CI=1 npm run test:e2e
```

## Test Coverage

### 1. Login Flow (01-login.spec.ts)
- ✅ Display login page
- ✅ Show error on invalid credentials
- ✅ Successful login with valid credentials
- ✅ Successful logout
- ✅ Redirect to login when accessing protected route
- ✅ Preserve redirect URL after login

### 2. Create Part Flow (02-create-part.spec.ts)
- ✅ Navigate to create part page
- ✅ Show validation errors for empty form
- ✅ Successfully create a new part
- ✅ Create part and navigate to detail view
- ✅ Cancel creation and return to list

### 3. Workspace Navigation (03-workspace-navigation.spec.ts)
- ✅ Display workspace with default module
- ✅ Switch between workspace modules
- ✅ Select part from parts list and update context
- ✅ Change workspace layout
- ✅ Persist selected part across module switches
- ✅ Show empty state when no part selected
- ✅ Switch modules with keyboard shortcuts
- ✅ Measure module switch performance (<100ms)

### 4. Batch Pricing Flow (04-batch-pricing.spec.ts)
- ✅ Display empty batches list initially
- ✅ Create a new batch
- ✅ Display batch cost breakdown
- ✅ Recalculate batch prices
- ✅ Delete a batch
- ✅ Create a batch set
- ✅ Add batch to batch set
- ✅ Freeze a batch set
- ✅ Display cost breakdown visualization

## Prerequisites

### Backend Running

E2E tests require the backend API to be running:

```bash
# Terminal 1: Start backend
cd /Users/lofas/Documents/__App_Claude/Gestima
python gestima.py run
```

### Test Data

Tests use auto-generated test data (see `helpers/test-data.ts`):
- Part numbers: `1XXXXXX` (7 digits, timestamp-based)
- Part names: `Test Part {timestamp}`
- Batch quantities: configurable

### Test User

Tests use default admin credentials:
- Username: `admin`
- Password: `admin123`

## Test Helpers

### `helpers/auth.ts`

```typescript
// Login helper
await login(page, 'admin', 'admin123');

// Logout helper
await logout(page);

// Check authentication
const isAuth = await isAuthenticated(page);
```

### `helpers/test-data.ts`

```typescript
// Generate unique part number
const partNumber = generatePartNumber(); // e.g., "1234567"

// Generate part data
const partData = generatePartData({
  name: 'Custom Name',
  description: 'Custom Description'
});

// Generate batch data
const batchData = generateBatchData(100); // quantity: 100
```

## Data Test IDs

All interactive elements use `data-testid` attributes for reliable selection:

### Login Page
- `username-input`
- `password-input`
- `login-button`

### Parts
- `create-part-button`
- `part-name-input`
- `part-description-input`
- `save-button`
- `cancel-button`
- `parts-table`
- `part-row`

### Workspace
- `workspace-container`
- `module-parts-list`
- `module-part-pricing`
- `module-part-operations`
- `module-part-material`
- `module-tab-{name}`
- `layout-picker-button`
- `layout-option-{name}`

### Batches
- `create-batch-button`
- `batch-quantity-input`
- `batches-table`
- `batch-row`
- `recalculate-button`
- `delete-batch-button`

### Batch Sets
- `create-batch-set-button`
- `batch-set-name-input`
- `batch-set-row`
- `freeze-batch-set-button`
- `add-batch-to-set-button`

### Common
- `toast` - Toast notifications
- `empty-state` - Empty state messages
- `user-menu` - User menu (authenticated)

## Performance Testing

Workspace navigation test includes performance measurement:

```typescript
test('should measure module switch performance', async ({ page }) => {
  const start = Date.now();
  await page.click('[data-testid="module-tab-pricing"]');
  await page.waitForSelector('[data-testid="module-part-pricing"]');
  const switchTime = Date.now() - start;

  expect(switchTime).toBeLessThan(100); // Target: <100ms
});
```

## Debugging

### Visual Debugging

```bash
# Run with headed browser
npx playwright test --headed

# Run with UI mode (best for debugging)
npx playwright test --ui
```

### Screenshots on Failure

Playwright automatically captures screenshots on test failure:
- Location: `test-results/`
- Format: PNG
- Includes full page screenshot

### Traces

Enable traces for debugging:

```bash
# Record trace for failed tests
npx playwright test --trace on-first-retry

# View trace
npx playwright show-trace trace.zip
```

## CI Integration

### GitHub Actions Example

```yaml
- name: Run E2E tests
  run: |
    npm run build:preview
    CI=1 npm run test:e2e
```

### Environment Variables

- `CI=1` - Runs headless, uses preview build (port 4173)
- `CI=0` - Runs headed, uses dev server (port 5173)

## Known Issues

### Test Isolation

Each test in `04-batch-pricing.spec.ts` uses `test.beforeAll` to create a shared test part. This improves performance but may cause issues if tests run in parallel. Consider using `test.describe.serial()` if needed.

### Timing Issues

If tests are flaky, increase timeout:

```typescript
test.setTimeout(60000); // 60 seconds
```

Or add explicit waits:

```typescript
await page.waitForSelector('[data-testid="element"]');
await page.waitForTimeout(500); // Last resort
```

## Next Steps

- [ ] Add visual regression testing (Percy/Chromatic)
- [ ] Add accessibility testing (axe-core)
- [ ] Add mobile viewport tests
- [ ] Add error scenario tests (network failures, API errors)
