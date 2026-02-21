import { test, expect } from '@playwright/test'
import { login } from './helpers/auth'
import { openModuleViaMenu, closeAllWindows, setupWindowsView, TIMEOUTS } from './helpers/windows'

test.describe('Workspace Navigation', () => {
  test.beforeEach(async ({ page }) => {
    await login(page)
    await setupWindowsView(page)
  })

  test('should display empty workspace with no windows', async ({ page }) => {
    const emptyState = page.locator('.empty-state')
    await expect(emptyState).toBeVisible()
  })

  test('should open Part Main module via menu', async ({ page }) => {
    await openModuleViaMenu(page, 'Part Main')

    const floatingWindow = page.locator('.floating-window')
    await expect(floatingWindow).toBeVisible()

    // Window should have a title
    const windowTitle = floatingWindow.locator('.window-title')
    await expect(windowTitle).toBeVisible()
  })

  test('should open multiple modules and switch focus', async ({ page }) => {
    await openModuleViaMenu(page, 'Part Main')
    await openModuleViaMenu(page, 'Nabídky')

    const windows = page.locator('.floating-window')
    await expect(windows).toHaveCount(2)

    // Click on first window to bring to front
    await windows.first().locator('.window-titlebar').click()

    // First window should have higher z-index
    const zIndex1 = await windows.first().evaluate(el => parseInt(el.style.zIndex || '0'))
    const zIndex2 = await windows.last().evaluate(el => parseInt(el.style.zIndex || '0'))
    expect(zIndex1).toBeGreaterThan(zIndex2)
  })

  test('should close all windows and show empty state', async ({ page }) => {
    await openModuleViaMenu(page, 'Admin')
    await expect(page.locator('.floating-window')).toBeVisible()

    await closeAllWindows(page)

    const emptyState = page.locator('.empty-state')
    await expect(emptyState).toBeVisible()
  })

  test('should navigate to settings and back', async ({ page }) => {
    // Open menu
    await page.click('.menu-btn')
    await expect(page.locator('.menu-drawer')).toBeVisible()

    // Click settings
    await page.locator('.settings-btn').click()

    // Should navigate to settings
    await page.waitForSelector('.settings-view, .page-title', { state: 'visible', timeout: TIMEOUTS.API_LOAD })

    // Go back to windows via menu
    await page.click('.menu-btn')
    await expect(page.locator('.menu-drawer')).toBeVisible()
    await page.locator('.menu-item', { hasText: 'Admin' }).click()

    // Should open a floating window
    await expect(page.locator('.floating-window')).toBeVisible({ timeout: TIMEOUTS.WINDOW_OPEN })
  })
})
