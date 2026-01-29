import { Page } from '@playwright/test';

/**
 * Login helper - performs login flow
 */
export async function login(page: Page, username = 'admin', password = 'admin123') {
  await page.goto('/login');

  await page.fill('[data-testid="username-input"]', username);
  await page.fill('[data-testid="password-input"]', password);
  await page.click('[data-testid="login-button"]');

  // Wait for redirect to dashboard
  await page.waitForURL('/');
}

/**
 * Logout helper
 */
export async function logout(page: Page) {
  await page.click('[data-testid="user-menu-button"]');
  await page.click('[data-testid="logout-button"]');

  // Wait for redirect to login
  await page.waitForURL('/login');
}

/**
 * Check if user is authenticated
 */
export async function isAuthenticated(page: Page): Promise<boolean> {
  const userMenu = page.locator('[data-testid="user-menu"]');
  return await userMenu.isVisible();
}
