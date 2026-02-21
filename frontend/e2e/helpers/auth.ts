import { Page } from '@playwright/test';

/**
 * Login helper - navigates to the app.
 * With storageState configured in playwright.config.ts, the browser context
 * already has auth cookies. This function just ensures we're on the right page.
 * Falls back to actual login if cookies are expired.
 */
export async function login(page: Page, username = 'demo', password = 'demo123') {
  await page.goto('/windows');

  // Check if already authenticated (storageState)
  const menuBtn = page.locator('.menu-btn');
  const isAuth = await menuBtn.isVisible({ timeout: 3000 }).catch(() => false);

  if (isAuth) return;

  // Fallback: perform actual login
  await page.goto('/login');
  await page.waitForSelector('[data-testid="username-input"]', { state: 'visible', timeout: 10000 });
  await page.fill('[data-testid="username-input"]', username);
  await page.fill('[data-testid="password-input"]', password);
  await page.click('[data-testid="login-button"]');
  await page.waitForSelector('.menu-btn', { state: 'visible', timeout: 15000 });
}

/**
 * Logout helper
 */
export async function logout(page: Page) {
  await page.click('.menu-btn');
  await page.waitForSelector('.menu-drawer', { state: 'visible' });
  await page.click('.logout-btn');
  await page.waitForSelector('[data-testid="login-button"]', { state: 'visible', timeout: 10000 });
}

/**
 * Check if user is authenticated
 */
export async function isAuthenticated(page: Page): Promise<boolean> {
  const menuBtn = page.locator('.menu-btn');
  return await menuBtn.isVisible();
}
