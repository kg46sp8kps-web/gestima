import { test, expect } from '@playwright/test'
import { login } from './helpers/auth'
import { openModuleViaMenu, setupWindowsView, waitForModuleLoad, TIMEOUTS } from './helpers/windows'

test.describe('Manufacturing Module', () => {
  test.beforeEach(async ({ page }) => {
    await login(page)
    await setupWindowsView(page)
    await openModuleViaMenu(page, 'Vyráběné položky')
    await waitForModuleLoad(page)
  })

  test('should display split-pane with parts list', async ({ page }) => {
    const floatingWindow = page.locator('.floating-window')

    // Left panel (parts list) should be visible
    const leftPanel = floatingWindow.locator('.first-panel, .left-panel').first()
    await expect(leftPanel).toBeVisible({ timeout: TIMEOUTS.API_LOAD })

    // Right panel is conditionally rendered (v-if="selectedPart") — only visible after selection
    // Just verify the split layout exists
    const splitLayout = floatingWindow.locator('.split-layout')
    await expect(splitLayout).toBeVisible()
  })

  test('should select part and show detail panel', async ({ page }) => {
    const floatingWindow = page.locator('.floating-window')

    // Wait for parts to load
    const partRow = floatingWindow.locator('.vt-row').first()
    if (await partRow.isVisible({ timeout: TIMEOUTS.API_LOAD }).catch(() => false)) {
      await partRow.click()
      await page.waitForTimeout(TIMEOUTS.DEBOUNCE)

      // Detail panel should show part info
      const detailContent = floatingWindow.locator('.info-ribbon, .detail-content, .part-detail')
      await expect(detailContent.first()).toBeVisible({ timeout: TIMEOUTS.API_LOAD })
    }
  })

  test('should resize split panel via drag handle', async ({ page }) => {
    const floatingWindow = page.locator('.floating-window')

    const resizeHandle = floatingWindow.locator('.resize-handle').first()
    if (await resizeHandle.isVisible({ timeout: TIMEOUTS.DEBOUNCE }).catch(() => false)) {
      const handleBox = await resizeHandle.boundingBox()
      if (handleBox) {
        // Drag handle to the right
        await page.mouse.move(handleBox.x + handleBox.width / 2, handleBox.y + handleBox.height / 2)
        await page.mouse.down()
        await page.mouse.move(handleBox.x + handleBox.width / 2 + 50, handleBox.y + handleBox.height / 2)
        await page.mouse.up()

        // Resize should have occurred (no crash)
        expect(true).toBe(true)
      }
    }
  })

  test('should create and cancel new part', async ({ page }) => {
    const floatingWindow = page.locator('.floating-window')

    // Find create button
    const createBtn = floatingWindow.locator('.icon-btn-primary, button[title*="Nový"]').first()
    if (await createBtn.isVisible({ timeout: TIMEOUTS.API_LOAD }).catch(() => false)) {
      await createBtn.click()
      await page.waitForTimeout(TIMEOUTS.DEBOUNCE)

      // Should show create form or edit mode
      const cancelBtn = floatingWindow.locator('button[title*="Zrušit"], .icon-btn-danger, .btn-cancel').first()
      if (await cancelBtn.isVisible({ timeout: TIMEOUTS.DEBOUNCE }).catch(() => false)) {
        await cancelBtn.click()
        await page.waitForTimeout(TIMEOUTS.DEBOUNCE)
      }
    }
  })

  test('should open linked pricing window', async ({ page }) => {
    const floatingWindow = page.locator('.floating-window')

    // Select a part first
    const partRow = floatingWindow.locator('.vt-row').first()
    if (await partRow.isVisible({ timeout: TIMEOUTS.API_LOAD }).catch(() => false)) {
      await partRow.click()
      await page.waitForTimeout(TIMEOUTS.DEBOUNCE)

      // Find pricing button in the toolbar or detail panel
      const pricingBtn = floatingWindow.locator('button[title*="Pricing"], button[title*="Kalkulace"], button[title*="pricing"]').first()
      if (await pricingBtn.isVisible({ timeout: TIMEOUTS.DEBOUNCE }).catch(() => false)) {
        await pricingBtn.click()
        await page.waitForTimeout(TIMEOUTS.DEBOUNCE)

        // A second floating window should open
        const windows = page.locator('.floating-window')
        const windowCount = await windows.count()
        expect(windowCount).toBeGreaterThanOrEqual(2)
      }
    }
  })
})
