import { test, expect } from '@playwright/test'
import { login } from './helpers/auth'
import {
  openModuleViaMenu,
  openModuleViaSearch,
  closeAllWindows,
  setupWindowsView,
  TIMEOUTS
} from './helpers/windows'

test.describe('Floating Windows System', () => {
  test.beforeEach(async ({ page }) => {
    await login(page)
    await setupWindowsView(page)
  })

  test('should show empty state when no windows open', async ({ page }) => {
    const emptyState = page.locator('.empty-state')
    await expect(emptyState).toBeVisible()
    await expect(emptyState).toContainText('No Windows Open')
  })

  test('should open module window via menu', async ({ page }) => {
    // Click hamburger menu
    await page.click('.menu-btn')
    await expect(page.locator('.menu-drawer')).toBeVisible()

    // Click a module item
    const menuItem = page.locator('.menu-item', { hasText: 'Nabídky' })
    await menuItem.click()

    // Floating window should appear
    const floatingWindow = page.locator('.floating-window')
    await expect(floatingWindow).toBeVisible({ timeout: TIMEOUTS.WINDOW_OPEN })

    // Window should have a title
    const windowTitle = floatingWindow.locator('.window-title')
    await expect(windowTitle).toBeVisible()
  })

  test('should open module window via search bar', async ({ page }) => {
    const searchInput = page.locator('.search-container .search-input')
    await searchInput.fill('Admin')

    // Dropdown should appear
    await expect(page.locator('.search-results')).toBeVisible()

    // Click result
    const resultItem = page.locator('.search-result-item', { hasText: 'Admin' }).first()
    await resultItem.click()

    // Window should appear
    await expect(page.locator('.floating-window')).toBeVisible({ timeout: TIMEOUTS.WINDOW_OPEN })
  })

  test('should close a window with close button', async ({ page }) => {
    await openModuleViaMenu(page, 'Admin')
    await expect(page.locator('.floating-window')).toHaveCount(1)

    // Click close button
    await page.locator('.floating-window .btn-close').click()

    // Handle potential save defaults modal
    const cancelBtn = page.locator('.modal-overlay .btn-secondary')
    if (await cancelBtn.isVisible({ timeout: 300 }).catch(() => false)) {
      await cancelBtn.click()
    }

    // Window should be removed
    await expect(page.locator('.floating-window')).toHaveCount(0, { timeout: TIMEOUTS.ANIMATION })
  })

  test('should minimize window', async ({ page }) => {
    await openModuleViaMenu(page, 'Admin')
    const floatingWindow = page.locator('.floating-window')
    await expect(floatingWindow).toBeVisible()

    // Click minimize
    await floatingWindow.locator('.btn-minimize').click()

    // Window should be hidden (v-show=false)
    await expect(floatingWindow).toBeHidden()
  })

  test('should maximize and restore a window', async ({ page }) => {
    await openModuleViaMenu(page, 'Admin')
    const floatingWindow = page.locator('.floating-window')

    // Not maximized initially
    await expect(floatingWindow).not.toHaveClass(/is-maximized/)

    // Click maximize
    await floatingWindow.locator('.btn-maximize').click()
    await expect(floatingWindow).toHaveClass(/is-maximized/)

    // Click again to restore
    await floatingWindow.locator('.btn-maximize').click()
    await expect(floatingWindow).not.toHaveClass(/is-maximized/)
  })

  test('should bring window to front on click', async ({ page }) => {
    // Open two windows
    await openModuleViaMenu(page, 'Admin')
    await openModuleViaMenu(page, 'Nabídky')

    const windows = page.locator('.floating-window')
    await expect(windows).toHaveCount(2)

    // Get z-indexes
    const firstWindow = windows.first()
    const secondWindow = windows.last()

    // Click on the first window's titlebar
    await firstWindow.locator('.window-titlebar').click()

    // First window should now have higher z-index
    const zIndex1 = await firstWindow.evaluate(el => parseInt(el.style.zIndex || '0'))
    const zIndex2 = await secondWindow.evaluate(el => parseInt(el.style.zIndex || '0'))
    expect(zIndex1).toBeGreaterThan(zIndex2)
  })

  test('should open multiple windows simultaneously', async ({ page }) => {
    await openModuleViaMenu(page, 'Admin')
    await openModuleViaMenu(page, 'Nabídky')
    await openModuleViaMenu(page, 'Zákazníci')

    const windows = page.locator('.floating-window')
    await expect(windows).toHaveCount(3)
  })

  test('should set linking group via color dot', async ({ page }) => {
    await openModuleViaMenu(page, 'Part Main')
    const floatingWindow = page.locator('.floating-window')

    // Click the linking dot
    await floatingWindow.locator('.linking-dot').click()

    // Color dropdown should appear (teleported to body)
    const colorDropdown = page.locator('.color-dropdown-teleported')
    await expect(colorDropdown).toBeVisible()

    // Click "Red" option
    const redOption = colorDropdown.locator('.color-option').first()
    await redOption.click()

    // Dropdown should close
    await expect(colorDropdown).toBeHidden()
  })

  test('should close menu by clicking backdrop', async ({ page }) => {
    // Open menu
    await page.click('.menu-btn')
    await expect(page.locator('.menu-drawer')).toBeVisible()

    // Click backdrop
    await page.locator('.backdrop').click()

    // Menu should close
    await expect(page.locator('.menu-drawer')).toBeHidden()
  })
})
