import { Page, expect } from '@playwright/test'

/** Timeout constants for E2E tests */
export const TIMEOUTS = {
  DEBOUNCE: 400,
  ANIMATION: 500,
  API_LOAD: 5000,
  WINDOW_OPEN: 3000,
}

/**
 * Open a module window via the hamburger menu.
 * @param page Playwright page
 * @param moduleLabel Exact label text as shown in AppMainMenu (e.g. "Nabídky", "Admin")
 */
export async function openModuleViaMenu(page: Page, moduleLabel: string) {
  // Open menu drawer
  await page.click('.menu-btn')
  await page.waitForSelector('.menu-drawer', { state: 'visible', timeout: TIMEOUTS.ANIMATION })

  // Click the module item matching the label
  const menuItem = page.locator('.menu-item', { hasText: moduleLabel })
  await menuItem.click()

  // Wait for floating window to appear
  await page.waitForSelector('.floating-window', { state: 'visible', timeout: TIMEOUTS.WINDOW_OPEN })

  // Wait for window content to load
  await page.waitForSelector('.window-content', { state: 'visible', timeout: TIMEOUTS.API_LOAD })
}

/**
 * Open a module window via the search bar.
 * @param page Playwright page
 * @param moduleLabel Label text to search for
 */
export async function openModuleViaSearch(page: Page, moduleLabel: string) {
  const searchInput = page.locator('.search-container .search-input')
  await searchInput.fill(moduleLabel)

  // Wait for dropdown to appear
  await page.waitForSelector('.search-results', { state: 'visible', timeout: TIMEOUTS.ANIMATION })

  // Click the first matching result
  const resultItem = page.locator('.search-result-item', { hasText: moduleLabel }).first()
  await resultItem.click()

  // Wait for floating window
  await page.waitForSelector('.floating-window', { state: 'visible', timeout: TIMEOUTS.WINDOW_OPEN })
}

/**
 * Close all open floating windows.
 */
export async function closeAllWindows(page: Page) {
  const closeButtons = page.locator('.floating-window .btn-close')
  const count = await closeButtons.count()

  for (let i = count - 1; i >= 0; i--) {
    // Click close, handle potential "save defaults" modal
    await closeButtons.nth(i).click()

    // If save defaults modal appears, click cancel (don't save)
    const cancelBtn = page.locator('.modal-overlay .btn-secondary', { hasText: 'Ne' })
    if (await cancelBtn.isVisible({ timeout: 300 }).catch(() => false)) {
      await cancelBtn.click()
    }
  }

  // Wait until no floating windows remain
  await expect(page.locator('.floating-window')).toHaveCount(0, { timeout: TIMEOUTS.ANIMATION })
}

/**
 * Get the count of currently visible floating windows.
 */
export async function getWindowCount(page: Page): Promise<number> {
  return page.locator('.floating-window:visible').count()
}

/**
 * Wait for a module's content to finish loading (spinner gone).
 * Uses a generic approach — waits for any loading spinner to disappear.
 */
export async function waitForModuleLoad(page: Page) {
  // Wait a beat for loading state to start
  await page.waitForTimeout(100)

  // Wait for any loading spinners to disappear
  const spinner = page.locator('.loading-list, .loading-state, .loading-container').first()
  if (await spinner.isVisible({ timeout: 200 }).catch(() => false)) {
    await spinner.waitFor({ state: 'hidden', timeout: TIMEOUTS.API_LOAD })
  }
}

/**
 * Navigate to /windows and ensure a clean state (logged in, no windows open).
 */
export async function setupWindowsView(page: Page) {
  await page.goto('/windows')

  // Wait for the page to be ready (menu button visible = authenticated + rendered)
  await page.waitForSelector('.menu-btn', { state: 'visible', timeout: 10000 })

  // Close any windows that may have auto-loaded from a saved layout
  await page.waitForTimeout(500) // Let any default layout load
  const windowCount = await page.locator('.floating-window').count()
  if (windowCount > 0) {
    await closeAllWindows(page)
  }
}
