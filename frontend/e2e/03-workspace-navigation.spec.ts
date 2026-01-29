import { test, expect } from '@playwright/test';
import { login } from './helpers/auth';

test.describe('Workspace Navigation', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto('/workspace');
  });

  test('should display workspace with default module', async ({ page }) => {
    // Should be on workspace route
    await expect(page).toHaveURL('/workspace');

    // Should show workspace layout
    await expect(page.locator('[data-testid="workspace-container"]')).toBeVisible();

    // Should show default module (parts-list)
    await expect(page.locator('[data-testid="module-parts-list"]')).toBeVisible();
  });

  test('should switch between workspace modules', async ({ page }) => {
    // Default: parts-list module
    await expect(page.locator('[data-testid="module-parts-list"]')).toBeVisible();

    // Click on pricing module tab
    await page.click('[data-testid="module-tab-pricing"]');

    // Should show pricing module
    await expect(page.locator('[data-testid="module-part-pricing"]')).toBeVisible();
    await expect(page.locator('[data-testid="module-parts-list"]')).not.toBeVisible();

    // Click on operations module tab
    await page.click('[data-testid="module-tab-operations"]');

    // Should show operations module
    await expect(page.locator('[data-testid="module-part-operations"]')).toBeVisible();
    await expect(page.locator('[data-testid="module-part-pricing"]')).not.toBeVisible();
  });

  test('should select part from parts list and update context', async ({ page }) => {
    // Wait for parts list to load
    await page.waitForSelector('[data-testid="parts-table"]');

    // Click on first part row
    await page.click('[data-testid="part-row"]:first-child');

    // Should update workspace context
    await expect(page.locator('[data-testid="selected-part-name"]')).toBeVisible();

    // Switch to pricing module
    await page.click('[data-testid="module-tab-pricing"]');

    // Pricing module should show data for selected part
    await expect(page.locator('[data-testid="module-part-pricing"]')).toBeVisible();
    await expect(page.locator('[data-testid="pricing-part-name"]')).toBeVisible();
  });

  test('should change workspace layout', async ({ page }) => {
    // Open layout picker
    await page.click('[data-testid="layout-picker-button"]');

    // Select layout (e.g., "2 columns")
    await page.click('[data-testid="layout-option-2col"]');

    // Workspace should update layout
    await expect(page.locator('[data-testid="workspace-container"]')).toHaveClass(/layout-2col/);

    // Both panels should be visible
    await expect(page.locator('[data-testid="workspace-panel-1"]')).toBeVisible();
    await expect(page.locator('[data-testid="workspace-panel-2"]')).toBeVisible();
  });

  test('should persist selected part across module switches', async ({ page }) => {
    // Select a part
    await page.waitForSelector('[data-testid="parts-table"]');
    await page.click('[data-testid="part-row"]:first-child');

    const selectedPartName = await page.locator('[data-testid="selected-part-name"]').textContent();

    // Switch to operations module
    await page.click('[data-testid="module-tab-operations"]');
    await expect(page.locator('[data-testid="operations-part-name"]')).toContainText(selectedPartName || '');

    // Switch to material module
    await page.click('[data-testid="module-tab-material"]');
    await expect(page.locator('[data-testid="material-part-name"]')).toContainText(selectedPartName || '');

    // Switch to pricing module
    await page.click('[data-testid="module-tab-pricing"]');
    await expect(page.locator('[data-testid="pricing-part-name"]')).toContainText(selectedPartName || '');
  });

  test('should show empty state when no part selected in non-parts-list modules', async ({ page }) => {
    // Switch to pricing module (no part selected)
    await page.click('[data-testid="module-tab-pricing"]');

    // Should show empty state
    await expect(page.locator('[data-testid="empty-state"]')).toBeVisible();
    await expect(page.locator('[data-testid="empty-state"]')).toContainText('Vyberte díl');
  });

  test('should switch modules with keyboard shortcuts', async ({ page }) => {
    // Tab 1: Pricing (Ctrl+1)
    await page.keyboard.press('Control+1');
    await expect(page.locator('[data-testid="module-part-pricing"]')).toBeVisible();

    // Tab 2: Operations (Ctrl+2)
    await page.keyboard.press('Control+2');
    await expect(page.locator('[data-testid="module-part-operations"]')).toBeVisible();

    // Tab 3: Material (Ctrl+3)
    await page.keyboard.press('Control+3');
    await expect(page.locator('[data-testid="module-part-material"]')).toBeVisible();

    // Tab 0: Parts List (Ctrl+0)
    await page.keyboard.press('Control+0');
    await expect(page.locator('[data-testid="module-parts-list"]')).toBeVisible();
  });

  test('should measure module switch performance', async ({ page }) => {
    // Select a part first
    await page.waitForSelector('[data-testid="parts-table"]');
    await page.click('[data-testid="part-row"]:first-child');

    // Measure switch time
    const start = Date.now();

    await page.click('[data-testid="module-tab-pricing"]');
    await page.waitForSelector('[data-testid="module-part-pricing"]');

    const switchTime = Date.now() - start;

    // Should be fast (<100ms per spec)
    expect(switchTime).toBeLessThan(100);
  });
});
