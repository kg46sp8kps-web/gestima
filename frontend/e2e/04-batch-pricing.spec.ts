import { test, expect } from '@playwright/test';
import { login } from './helpers/auth';
import { generatePartData, generateBatchData } from './helpers/test-data';

test.describe('Batch Pricing Flow', () => {
  let partNumber: string;

  test.beforeAll(async ({ browser }) => {
    // Create a test part for batch pricing tests
    const page = await browser.newPage();
    await login(page);

    await page.goto('/parts/new');
    const partData = generatePartData({ name: 'Batch Test Part' });

    await page.fill('[data-testid="part-name-input"]', partData.name);
    await page.fill('[data-testid="part-description-input"]', partData.description);
    await page.click('[data-testid="save-button"]');

    await page.waitForURL(/\/parts\/(\d+)/);
    const url = page.url();
    const match = url.match(/\/parts\/(\d+)/);
    partNumber = match?.[1] || '';

    await page.close();
  });

  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto('/workspace');

    // Select the test part
    await page.waitForSelector('[data-testid="parts-table"]');

    // Search for our test part
    await page.fill('[data-testid="search-input"]', partNumber);
    await page.waitForTimeout(500); // Wait for debounced search

    // Click on the part
    await page.click('[data-testid="part-row"]:first-child');

    // Switch to pricing module
    await page.click('[data-testid="module-tab-pricing"]');
    await page.waitForSelector('[data-testid="module-part-pricing"]');
  });

  test('should display empty batches list initially', async ({ page }) => {
    // Should show empty state or batches table
    const batchesTable = page.locator('[data-testid="batches-table"]');
    const emptyState = page.locator('[data-testid="empty-batches"]');

    const hasTable = await batchesTable.isVisible();
    const hasEmptyState = await emptyState.isVisible();

    expect(hasTable || hasEmptyState).toBe(true);
  });

  test('should create a new batch', async ({ page }) => {
    // Click create batch button
    await page.click('[data-testid="create-batch-button"]');

    // Fill in quantity
    const batchData = generateBatchData(100);
    await page.fill('[data-testid="batch-quantity-input"]', batchData.quantity.toString());

    // Submit
    await page.click('[data-testid="save-batch-button"]');

    // Should show success toast
    await expect(page.locator('[data-testid="toast"]')).toBeVisible();
    await expect(page.locator('[data-testid="toast"]')).toContainText('úspěšně');

    // Should show batch in table
    await expect(page.locator('[data-testid="batch-row"]')).toBeVisible();
    await expect(page.locator('[data-testid="batch-quantity"]')).toContainText('100');
  });

  test('should display batch cost breakdown', async ({ page }) => {
    // Create a batch first
    await page.click('[data-testid="create-batch-button"]');
    await page.fill('[data-testid="batch-quantity-input"]', '50');
    await page.click('[data-testid="save-batch-button"]');

    await page.waitForSelector('[data-testid="batch-row"]');

    // Click on batch to see details
    await page.click('[data-testid="batch-row"]:first-child');

    // Should show cost breakdown
    await expect(page.locator('[data-testid="cost-breakdown"]')).toBeVisible();
    await expect(page.locator('[data-testid="material-cost"]')).toBeVisible();
    await expect(page.locator('[data-testid="operation-cost"]')).toBeVisible();
    await expect(page.locator('[data-testid="total-cost"]')).toBeVisible();
  });

  test('should recalculate batch prices', async ({ page }) => {
    // Create a batch
    await page.click('[data-testid="create-batch-button"]');
    await page.fill('[data-testid="batch-quantity-input"]', '25');
    await page.click('[data-testid="save-batch-button"]');

    await page.waitForSelector('[data-testid="batch-row"]');

    // Click recalculate button
    await page.click('[data-testid="recalculate-button"]');

    // Should show success toast
    await expect(page.locator('[data-testid="toast"]')).toBeVisible();
    await expect(page.locator('[data-testid="toast"]')).toContainText('přepočítány');
  });

  test('should delete a batch', async ({ page }) => {
    // Create a batch
    await page.click('[data-testid="create-batch-button"]');
    await page.fill('[data-testid="batch-quantity-input"]', '10');
    await page.click('[data-testid="save-batch-button"]');

    await page.waitForSelector('[data-testid="batch-row"]');
    const initialCount = await page.locator('[data-testid="batch-row"]').count();

    // Click delete button on first batch
    await page.click('[data-testid="delete-batch-button"]:first-child');

    // Confirm deletion
    await page.click('[data-testid="confirm-delete-button"]');

    // Should show success toast
    await expect(page.locator('[data-testid="toast"]')).toBeVisible();

    // Batch count should decrease
    const newCount = await page.locator('[data-testid="batch-row"]').count();
    expect(newCount).toBe(initialCount - 1);
  });

  test('should create a batch set', async ({ page }) => {
    // Switch to batch sets module
    await page.click('[data-testid="module-tab-batch-sets"]');

    // Click create batch set button
    await page.click('[data-testid="create-batch-set-button"]');

    // Fill in batch set name
    await page.fill('[data-testid="batch-set-name-input"]', 'Test Batch Set');

    // Submit
    await page.click('[data-testid="save-batch-set-button"]');

    // Should show success toast
    await expect(page.locator('[data-testid="toast"]')).toBeVisible();

    // Should show batch set in list
    await expect(page.locator('[data-testid="batch-set-row"]')).toBeVisible();
    await expect(page.locator('[data-testid="batch-set-name"]')).toContainText('Test Batch Set');
  });

  test('should add batch to batch set', async ({ page }) => {
    // First, create a batch
    await page.click('[data-testid="create-batch-button"]');
    await page.fill('[data-testid="batch-quantity-input"]', '75');
    await page.click('[data-testid="save-batch-button"]');
    await page.waitForSelector('[data-testid="batch-row"]');

    // Switch to batch sets
    await page.click('[data-testid="module-tab-batch-sets"]');

    // Create a batch set
    await page.click('[data-testid="create-batch-set-button"]');
    await page.fill('[data-testid="batch-set-name-input"]', 'Set with Batches');
    await page.click('[data-testid="save-batch-set-button"]');

    await page.waitForSelector('[data-testid="batch-set-row"]');

    // Click on batch set to view details
    await page.click('[data-testid="batch-set-row"]:first-child');

    // Click add batch button
    await page.click('[data-testid="add-batch-to-set-button"]');

    // Select batch (quantity 75)
    await page.click('[data-testid="batch-select-option-75"]');

    // Confirm
    await page.click('[data-testid="confirm-add-batch-button"]');

    // Should show batch in set
    await expect(page.locator('[data-testid="batch-in-set"]')).toBeVisible();
    await expect(page.locator('[data-testid="batch-in-set-quantity"]')).toContainText('75');
  });

  test('should freeze a batch set', async ({ page }) => {
    // Switch to batch sets
    await page.click('[data-testid="module-tab-batch-sets"]');

    // Create a batch set
    await page.click('[data-testid="create-batch-set-button"]');
    await page.fill('[data-testid="batch-set-name-input"]', 'Set to Freeze');
    await page.click('[data-testid="save-batch-set-button"]');

    await page.waitForSelector('[data-testid="batch-set-row"]');

    // Click freeze button
    await page.click('[data-testid="freeze-batch-set-button"]:first-child');

    // Confirm freeze
    await page.click('[data-testid="confirm-freeze-button"]');

    // Should show success toast
    await expect(page.locator('[data-testid="toast"]')).toBeVisible();
    await expect(page.locator('[data-testid="toast"]')).toContainText('zmrazena');

    // Status should be frozen
    await expect(page.locator('[data-testid="batch-set-status"]')).toContainText('Frozen');
  });

  test('should display cost breakdown visualization', async ({ page }) => {
    // Create a batch with costs
    await page.click('[data-testid="create-batch-button"]');
    await page.fill('[data-testid="batch-quantity-input"]', '200');
    await page.click('[data-testid="save-batch-button"]');

    await page.waitForSelector('[data-testid="batch-row"]');

    // Should show cost bar chart
    await expect(page.locator('[data-testid="cost-breakdown-chart"]')).toBeVisible();

    // Should show material cost bar
    await expect(page.locator('[data-testid="material-cost-bar"]')).toBeVisible();

    // Should show operation cost bar
    await expect(page.locator('[data-testid="operation-cost-bar"]')).toBeVisible();
  });
});
