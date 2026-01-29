import { test, expect } from '@playwright/test';
import { login, logout } from './helpers/auth';
import { TEST_CREDENTIALS } from './helpers/test-data';

test.describe('Login Flow', () => {
  test('should display login page', async ({ page }) => {
    await page.goto('/login');

    // Check login form elements exist
    await expect(page.locator('[data-testid="username-input"]')).toBeVisible();
    await expect(page.locator('[data-testid="password-input"]')).toBeVisible();
    await expect(page.locator('[data-testid="login-button"]')).toBeVisible();
  });

  test('should show error on invalid credentials', async ({ page }) => {
    await page.goto('/login');

    await page.fill('[data-testid="username-input"]', 'invalid');
    await page.fill('[data-testid="password-input"]', 'invalid');
    await page.click('[data-testid="login-button"]');

    // Should show error toast
    await expect(page.locator('[data-testid="toast"]')).toBeVisible();
    await expect(page.locator('[data-testid="toast"]')).toContainText('Nesprávné');
  });

  test('should successfully login with valid credentials', async ({ page }) => {
    await login(page);

    // Should redirect to dashboard
    await expect(page).toHaveURL('/');

    // Should show user menu
    await expect(page.locator('[data-testid="user-menu"]')).toBeVisible();
  });

  test('should successfully logout', async ({ page }) => {
    // Login first
    await login(page);

    // Logout
    await logout(page);

    // Should redirect to login
    await expect(page).toHaveURL('/login');

    // User menu should be gone
    await expect(page.locator('[data-testid="user-menu"]')).not.toBeVisible();
  });

  test('should redirect to login when accessing protected route while unauthenticated', async ({ page }) => {
    await page.goto('/parts');

    // Should redirect to login
    await expect(page).toHaveURL('/login');
  });

  test('should preserve redirect URL after login', async ({ page }) => {
    // Try to access protected route
    await page.goto('/parts');

    // Should redirect to login with redirect query
    await expect(page).toHaveURL(/\/login\?redirect=/);

    // Login
    await page.fill('[data-testid="username-input"]', TEST_CREDENTIALS.admin.username);
    await page.fill('[data-testid="password-input"]', TEST_CREDENTIALS.admin.password);
    await page.click('[data-testid="login-button"]');

    // Should redirect to original route
    await expect(page).toHaveURL('/parts');
  });
});
