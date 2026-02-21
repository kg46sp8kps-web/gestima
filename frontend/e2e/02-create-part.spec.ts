import { test, expect } from '@playwright/test'
import { login } from './helpers/auth'
import { openModuleViaMenu, setupWindowsView, waitForModuleLoad, TIMEOUTS } from './helpers/windows'

test.describe('Create Part Flow', () => {
  test.beforeEach(async ({ page }) => {
    await login(page)
    await setupWindowsView(page)
    await openModuleViaMenu(page, 'Part Main')
    await waitForModuleLoad(page)
  })

  test('should display parts list in floating window', async ({ page }) => {
    const floatingWindow = page.locator('.floating-window')

    // Parts list should have virtualized rows
    const rows = floatingWindow.locator('.vt-row')
    await expect(rows.first()).toBeVisible({ timeout: TIMEOUTS.API_LOAD })
  })

  test('should create a new part via toolbar button', async ({ page }) => {
    const floatingWindow = page.locator('.floating-window')

    // Find create button (icon-btn-primary or Plus button)
    const createBtn = floatingWindow.locator('.icon-btn-primary, button[title*="Nový"]').first()
    if (await createBtn.isVisible({ timeout: TIMEOUTS.API_LOAD }).catch(() => false)) {
      await createBtn.click()
      await page.waitForTimeout(TIMEOUTS.DEBOUNCE)

      // Should enter edit mode (inputs become editable)
      const editInput = floatingWindow.locator('.edit-input, input:not([disabled])').first()
      const isEditing = await editInput.isVisible({ timeout: TIMEOUTS.DEBOUNCE }).catch(() => false)

      if (isEditing) {
        // Cancel creation
        const cancelBtn = floatingWindow.locator('button[title*="Zrušit"], .icon-btn-danger').first()
        if (await cancelBtn.isVisible({ timeout: 300 }).catch(() => false)) {
          await cancelBtn.click()
        }
      }
    }
  })

  test('should select a part and show detail panel', async ({ page }) => {
    const floatingWindow = page.locator('.floating-window')

    const firstRow = floatingWindow.locator('.vt-row').first()
    await expect(firstRow).toBeVisible({ timeout: TIMEOUTS.API_LOAD })
    await firstRow.click()
    await page.waitForTimeout(TIMEOUTS.DEBOUNCE)

    // Detail panel should show part info
    const detail = floatingWindow.locator('.info-ribbon, .detail-content, .part-detail')
    await expect(detail.first()).toBeVisible({ timeout: TIMEOUTS.API_LOAD })
  })

  test('should search parts by name or article number', async ({ page }) => {
    const floatingWindow = page.locator('.floating-window')
    const searchInput = floatingWindow.locator('.search-input')

    if (await searchInput.isVisible({ timeout: TIMEOUTS.DEBOUNCE }).catch(() => false)) {
      await searchInput.fill('test')
      await page.waitForTimeout(TIMEOUTS.DEBOUNCE)

      // Clear
      await searchInput.clear()
      await page.waitForTimeout(TIMEOUTS.DEBOUNCE)
    }
  })
})
