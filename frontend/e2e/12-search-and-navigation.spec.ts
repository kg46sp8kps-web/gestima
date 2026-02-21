import { test, expect } from '@playwright/test'
import { login } from './helpers/auth'
import { setupWindowsView, TIMEOUTS } from './helpers/windows'

test.describe('Search & Navigation', () => {
  test.beforeEach(async ({ page }) => {
    await login(page)
    await setupWindowsView(page)
  })

  test('should display search bar in header', async ({ page }) => {
    const searchInput = page.locator('.search-container .search-input')
    await expect(searchInput).toBeVisible()
    await expect(searchInput).toHaveAttribute('placeholder', 'search modules')
  })

  test('should show module results on search', async ({ page }) => {
    const searchInput = page.locator('.search-container .search-input')
    await searchInput.focus()
    await searchInput.fill('Part')

    // Dropdown should appear
    const dropdown = page.locator('.search-results')
    await expect(dropdown).toBeVisible({ timeout: TIMEOUTS.ANIMATION })

    // Results should contain matching items
    const results = dropdown.locator('.search-result-item')
    const count = await results.count()
    expect(count).toBeGreaterThan(0)

    // Each result should contain "Part" in text
    for (let i = 0; i < count; i++) {
      const text = await results.nth(i).textContent()
      expect(text?.toLowerCase()).toContain('part')
    }
  })

  test('should open module from search result', async ({ page }) => {
    const searchInput = page.locator('.search-container .search-input')
    await searchInput.fill('Nabídky')

    await expect(page.locator('.search-results')).toBeVisible({ timeout: TIMEOUTS.ANIMATION })

    // Click the result
    await page.locator('.search-result-item', { hasText: 'Nabídky' }).click()

    // Floating window should appear
    await expect(page.locator('.floating-window')).toBeVisible({ timeout: TIMEOUTS.WINDOW_OPEN })
  })

  test('should clear search after selection', async ({ page }) => {
    const searchInput = page.locator('.search-container .search-input')
    await searchInput.fill('Admin')

    await expect(page.locator('.search-results')).toBeVisible({ timeout: TIMEOUTS.ANIMATION })
    await page.locator('.search-result-item', { hasText: 'Admin' }).click()

    // Search input should be cleared
    await expect(searchInput).toHaveValue('')

    // Dropdown should be hidden
    await expect(page.locator('.search-results')).toBeHidden()
  })

  test('should navigate to settings via menu', async ({ page }) => {
    // Open menu
    await page.click('.menu-btn')
    await expect(page.locator('.menu-drawer')).toBeVisible()

    // Click settings link
    await page.locator('.settings-btn').click()

    // Should navigate to /settings — wait for settings content to appear
    await page.waitForSelector('.settings-view, .page-title', { state: 'visible', timeout: TIMEOUTS.API_LOAD })
  })

  test('should navigate back to windows from settings', async ({ page }) => {
    // Go to settings
    await page.goto('/settings')
    await page.waitForSelector('.menu-btn', { state: 'visible', timeout: 10000 })

    // Open menu
    await page.click('.menu-btn')
    await expect(page.locator('.menu-drawer')).toBeVisible()

    // Click a module to go back to windows
    await page.locator('.menu-item', { hasText: 'Admin' }).click()

    // Should open a floating window
    await expect(page.locator('.floating-window')).toBeVisible({ timeout: TIMEOUTS.WINDOW_OPEN })
  })
})
