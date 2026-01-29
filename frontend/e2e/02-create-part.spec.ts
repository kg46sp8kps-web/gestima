import { test, expect } from '@playwright/test';
import { login } from './helpers/auth';
import { generatePartData } from './helpers/test-data';

test.describe('Create Part Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Login before each test
    await login(page);
  });

  test('should navigate to create part page', async ({ page }) => {
    // Navigate to parts list
    await page.goto('/parts');

    // Click create button
    await page.click('[data-testid="create-part-button"]');

    // Should be on create part page
    await expect(page).toHaveURL('/parts/new');
    await expect(page.locator('h1')).toContainText('Nový díl');
  });

  test('should show validation errors for empty form', async ({ page }) => {
    await page.goto('/parts/new');

    // Try to submit empty form
    await page.click('[data-testid="save-button"]');

    // Should show validation errors
    await expect(page.locator('[data-testid="error-name"]')).toBeVisible();
  });

  test('should successfully create a new part', async ({ page }) => {
    await page.goto('/parts/new');

    const partData = generatePartData();

    // Fill in part details
    await page.fill('[data-testid="part-name-input"]', partData.name);
    await page.fill('[data-testid="part-description-input"]', partData.description);

    // Submit form
    await page.click('[data-testid="save-button"]');

    // Should show success toast
    await expect(page.locator('[data-testid="toast"]')).toBeVisible();
    await expect(page.locator('[data-testid="toast"]')).toContainText('úspěšně');

    // Should redirect to part detail page
    await expect(page).toHaveURL(/\/parts\/\d+/);

    // Should show part name
    await expect(page.locator('[data-testid="part-name"]')).toContainText(partData.name);
  });

  test('should create part and navigate to detail view', async ({ page }) => {
    await page.goto('/parts/new');

    const partData = generatePartData({
      name: 'E2E Test Part',
      description: 'Created for E2E testing',
    });

    // Fill form
    await page.fill('[data-testid="part-name-input"]', partData.name);
    await page.fill('[data-testid="part-description-input"]', partData.description);

    // Submit
    await page.click('[data-testid="save-button"]');

    // Wait for redirect
    await page.waitForURL(/\/parts\/\d+/);

    // Should have 4 tabs
    await expect(page.locator('[data-testid="tab-basic"]')).toBeVisible();
    await expect(page.locator('[data-testid="tab-material"]')).toBeVisible();
    await expect(page.locator('[data-testid="tab-operations"]')).toBeVisible();
    await expect(page.locator('[data-testid="tab-pricing"]')).toBeVisible();

    // Basic tab should be active
    await expect(page.locator('[data-testid="tab-basic"]')).toHaveClass(/active/);
  });

  test('should cancel creation and return to list', async ({ page }) => {
    await page.goto('/parts/new');

    // Click cancel button
    await page.click('[data-testid="cancel-button"]');

    // Should return to parts list
    await expect(page).toHaveURL('/parts');
  });
});
