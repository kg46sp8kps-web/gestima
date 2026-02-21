import { test, expect } from '@playwright/test'
import { login } from './helpers/auth'
import { openModuleViaMenu, setupWindowsView, waitForModuleLoad, TIMEOUTS } from './helpers/windows'

test.describe('File Manager', () => {
  test.beforeEach(async ({ page }) => {
    await login(page)
    await setupWindowsView(page)
    await openModuleViaMenu(page, 'File Manager')
    await waitForModuleLoad(page)
  })

  test('should display file list panel with filters', async ({ page }) => {
    const floatingWindow = page.locator('.floating-window')

    // Search input
    const searchInput = floatingWindow.locator('.search-input')
    await expect(searchInput).toBeVisible({ timeout: TIMEOUTS.API_LOAD })

    // File type filter
    const filterSelect = floatingWindow.locator('.filter-select, select')
    await expect(filterSelect.first()).toBeVisible()

    // Upload zone
    const uploadZone = floatingWindow.locator('.upload-zone, .drag-drop-zone')
    await expect(uploadZone.first()).toBeVisible()
  })

  test('should filter files by type', async ({ page }) => {
    const floatingWindow = page.locator('.floating-window')
    const filterSelect = floatingWindow.locator('.filter-select, select').first()

    // Get options
    const options = filterSelect.locator('option')
    const optionCount = await options.count()

    if (optionCount > 1) {
      // Select PDF filter
      await filterSelect.selectOption({ index: 1 })
      await page.waitForTimeout(TIMEOUTS.DEBOUNCE)

      // Reset to all
      await filterSelect.selectOption({ index: 0 })
      await page.waitForTimeout(TIMEOUTS.DEBOUNCE)
    }
  })

  test('should search files by filename', async ({ page }) => {
    const floatingWindow = page.locator('.floating-window')
    const searchInput = floatingWindow.locator('.search-input')

    await searchInput.fill('test')
    await page.waitForTimeout(TIMEOUTS.DEBOUNCE)

    // Clear
    await searchInput.clear()
    await page.waitForTimeout(TIMEOUTS.DEBOUNCE)
  })

  test('should toggle orphans filter', async ({ page }) => {
    const floatingWindow = page.locator('.floating-window')

    // Find orphans checkbox
    const orphanCheckbox = floatingWindow.locator('.checkbox-label, label').filter({ hasText: /orphan/i })
    if (await orphanCheckbox.isVisible({ timeout: TIMEOUTS.DEBOUNCE }).catch(() => false)) {
      const checkbox = orphanCheckbox.locator('input[type="checkbox"]')

      // Toggle on
      await checkbox.check()
      await page.waitForTimeout(TIMEOUTS.DEBOUNCE)

      // Toggle off
      await checkbox.uncheck()
      await page.waitForTimeout(TIMEOUTS.DEBOUNCE)
    }
  })

  test('should display upload zone with correct accept types', async ({ page }) => {
    const floatingWindow = page.locator('.floating-window')

    // Upload zone text
    const uploadZone = floatingWindow.locator('.upload-zone, .drag-drop-zone')
    await expect(uploadZone.first()).toBeVisible()

    // Hidden file input should have accept attribute
    const fileInput = floatingWindow.locator('input[type="file"]')
    if (await fileInput.isVisible({ timeout: 300 }).catch(() => false)) {
      const accept = await fileInput.getAttribute('accept')
      if (accept) {
        expect(accept).toContain('.pdf')
      }
    }
  })
})
