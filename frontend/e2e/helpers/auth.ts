import { Page } from '@playwright/test';

/**
 * Login helper - performs login flow
 */
export async function login(page: Page, username = 'demo', password = 'demo123') {
  await page.goto('/login');

  // Wait for login form to be ready
  await page.waitForSelector('[data-testid="username-input"]', { state: 'visible', timeout: 10000 });

  await page.fill('[data-testid="username-input"]', username);
  await page.fill('[data-testid="password-input"]', password);
  await page.click('[data-testid="login-button"]');

  // Wait for SPA redirect — the menu button appears after successful login
  await page.waitForSelector('.menu-btn', { state: 'visible', timeout: 15000 });
}

/**
 * Logout helper
 */
export async function logout(page: Page) {
  // Open hamburger menu
  await page.click('.menu-btn');
  await page.waitForSelector('.menu-drawer', { state: 'visible' });

  // Click logout button in menu footer
  await page.click('.logout-btn');

  // Wait for login page to appear
  await page.waitForSelector('[data-testid="login-button"]', { state: 'visible', timeout: 10000 });
}

/**
 * Check if user is authenticated
 */
export async function isAuthenticated(page: Page): Promise<boolean> {
  const menuBtn = page.locator('.menu-btn');
  return await menuBtn.isVisible();
}
