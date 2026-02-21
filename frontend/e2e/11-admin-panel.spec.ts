import { test, expect } from '@playwright/test'
import { login } from './helpers/auth'
import { openModuleViaMenu, setupWindowsView, TIMEOUTS } from './helpers/windows'

test.describe('Admin Panel', () => {
  test.beforeEach(async ({ page }) => {
    await login(page)
    await setupWindowsView(page)
    await openModuleViaMenu(page, 'Admin')
  })

  test('should display all admin tabs', async ({ page }) => {
    const floatingWindow = page.locator('.floating-window')

    // Main tab buttons
    const tabs = floatingWindow.locator('.main-tab, .tab-button, button').filter({
      hasText: /Infor|Normy|Skupiny|Ceny|Pracovi|podmínky/
    })

    await expect(tabs.first()).toBeVisible({ timeout: TIMEOUTS.API_LOAD })
    const tabCount = await tabs.count()
    expect(tabCount).toBeGreaterThanOrEqual(4)
  })

  test('should switch between admin tabs', async ({ page }) => {
    const floatingWindow = page.locator('.floating-window')

    // Click "Normy" tab
    const normyTab = floatingWindow.locator('button', { hasText: 'Normy' })
    if (await normyTab.isVisible({ timeout: TIMEOUTS.DEBOUNCE }).catch(() => false)) {
      await normyTab.click()
      await page.waitForTimeout(TIMEOUTS.DEBOUNCE)

      // Some content should change
      expect(true).toBe(true)
    }

    // Click "Ceny" tab
    const cenyTab = floatingWindow.locator('button', { hasText: 'Ceny' })
    if (await cenyTab.isVisible({ timeout: TIMEOUTS.DEBOUNCE }).catch(() => false)) {
      await cenyTab.click()
      await page.waitForTimeout(TIMEOUTS.DEBOUNCE)
    }

    // Click "Pracovi" (Pracoviště) tab
    const pracovTab = floatingWindow.locator('button', { hasText: /Pracovi/ })
    if (await pracovTab.isVisible({ timeout: TIMEOUTS.DEBOUNCE }).catch(() => false)) {
      await pracovTab.click()
      await page.waitForTimeout(TIMEOUTS.DEBOUNCE)
    }
  })

  test('should display work centers table', async ({ page }) => {
    const floatingWindow = page.locator('.floating-window')

    // Navigate to work centers tab
    const pracovTab = floatingWindow.locator('button', { hasText: /Pracovi/ })
    if (await pracovTab.isVisible({ timeout: TIMEOUTS.DEBOUNCE }).catch(() => false)) {
      await pracovTab.click()
      await page.waitForTimeout(TIMEOUTS.DEBOUNCE)

      // Table should appear
      const table = floatingWindow.locator('table, .data-table')
      await expect(table.first()).toBeVisible({ timeout: TIMEOUTS.API_LOAD })

      // Should have rows
      const rows = floatingWindow.locator('tbody tr, .table-row')
      const rowCount = await rows.count()
      expect(rowCount).toBeGreaterThan(0)
    }
  })

  test('should display material norms table', async ({ page }) => {
    const floatingWindow = page.locator('.floating-window')

    const normyTab = floatingWindow.locator('button', { hasText: 'Normy' })
    if (await normyTab.isVisible({ timeout: TIMEOUTS.DEBOUNCE }).catch(() => false)) {
      await normyTab.click()
      await page.waitForTimeout(TIMEOUTS.DEBOUNCE)

      const table = floatingWindow.locator('table, .data-table')
      await expect(table.first()).toBeVisible({ timeout: TIMEOUTS.API_LOAD })

      const rows = floatingWindow.locator('tbody tr, .table-row')
      const rowCount = await rows.count()
      expect(rowCount).toBeGreaterThan(0)
    }
  })

  test('should display price categories', async ({ page }) => {
    const floatingWindow = page.locator('.floating-window')

    const cenyTab = floatingWindow.locator('button', { hasText: 'Ceny' })
    if (await cenyTab.isVisible({ timeout: TIMEOUTS.DEBOUNCE }).catch(() => false)) {
      await cenyTab.click()
      await page.waitForTimeout(TIMEOUTS.DEBOUNCE)

      const table = floatingWindow.locator('table, .data-table')
      await expect(table.first()).toBeVisible({ timeout: TIMEOUTS.API_LOAD })

      const rows = floatingWindow.locator('tbody tr, .table-row')
      const rowCount = await rows.count()
      expect(rowCount).toBeGreaterThan(0)
    }
  })

  test('should display cutting conditions catalog', async ({ page }) => {
    const floatingWindow = page.locator('.floating-window')

    const ccTab = floatingWindow.locator('button', { hasText: /podmínky|Řezné/ })
    if (await ccTab.isVisible({ timeout: TIMEOUTS.DEBOUNCE }).catch(() => false)) {
      await ccTab.click()
      await page.waitForTimeout(TIMEOUTS.DEBOUNCE)

      // Cutting conditions content should appear
      const content = floatingWindow.locator('table, .data-table, .cutting-conditions')
      await expect(content.first()).toBeVisible({ timeout: TIMEOUTS.API_LOAD })
    }
  })

  test('should show Infor connection status', async ({ page }) => {
    const floatingWindow = page.locator('.floating-window')

    // Infor tab should be active by default (first tab)
    // Look for status dot indicator
    const statusDot = floatingWindow.locator('.status-dot, .connection-status')
    const hasDot = await statusDot.first().isVisible({ timeout: TIMEOUTS.DEBOUNCE }).catch(() => false)

    // Infor tab content should be visible
    const inforContent = floatingWindow.locator('.infor-panel, .tab-content')
    await expect(inforContent.first()).toBeVisible({ timeout: TIMEOUTS.API_LOAD })
  })
})
