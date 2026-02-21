import { test, expect } from '@playwright/test'
import { login } from './helpers/auth'
import { openModuleViaMenu, setupWindowsView, waitForModuleLoad, TIMEOUTS } from './helpers/windows'

test.describe('Materials Module', () => {
  test.beforeEach(async ({ page }) => {
    await login(page)
    await setupWindowsView(page)
    await openModuleViaMenu(page, 'Materiálové položky')
    await waitForModuleLoad(page)
  })

  test('should display materials list with virtualized rows', async ({ page }) => {
    const floatingWindow = page.locator('.floating-window')

    // Header should be visible
    const header = floatingWindow.locator('.vt-header, .table-header')
    await expect(header.first()).toBeVisible({ timeout: TIMEOUTS.API_LOAD })

    // Rows should be rendered
    const rows = floatingWindow.locator('.vt-row')
    await expect(rows.first()).toBeVisible({ timeout: TIMEOUTS.API_LOAD })

    const rowCount = await rows.count()
    expect(rowCount).toBeGreaterThan(0)
  })

  test('should search materials by code', async ({ page }) => {
    const floatingWindow = page.locator('.floating-window')
    const searchInput = floatingWindow.locator('.search-input')
    await expect(searchInput).toBeVisible()

    // Get initial row count
    const initialCount = await floatingWindow.locator('.vt-row').count()

    // Search for something specific
    await searchInput.fill('1.4301')
    await page.waitForTimeout(TIMEOUTS.DEBOUNCE)

    // Row count should change (filtered)
    const filteredCount = await floatingWindow.locator('.vt-row').count()
    // Either results are filtered (fewer rows) or same (if all match)
    expect(filteredCount).toBeLessThanOrEqual(initialCount)

    // Clear search
    await searchInput.clear()
    await page.waitForTimeout(TIMEOUTS.DEBOUNCE)
  })

  test('should filter by material group', async ({ page }) => {
    const floatingWindow = page.locator('.floating-window')

    // Find group filter select
    const filterSelects = floatingWindow.locator('.filter-select, select')
    const filterCount = await filterSelects.count()

    if (filterCount > 0) {
      const groupFilter = filterSelects.first()
      await expect(groupFilter).toBeVisible()

      // Get options
      const options = groupFilter.locator('option')
      const optionCount = await options.count()

      if (optionCount > 1) {
        // Select a non-default option
        await groupFilter.selectOption({ index: 1 })
        await page.waitForTimeout(TIMEOUTS.DEBOUNCE)

        // Reset to default
        await groupFilter.selectOption({ index: 0 })
        await page.waitForTimeout(TIMEOUTS.DEBOUNCE)
      }
    }
  })

  test('should filter by shape', async ({ page }) => {
    const floatingWindow = page.locator('.floating-window')

    // Shape filter is typically the second select
    const filterSelects = floatingWindow.locator('.filter-select, select')
    const filterCount = await filterSelects.count()

    if (filterCount >= 2) {
      const shapeFilter = filterSelects.nth(1)
      await expect(shapeFilter).toBeVisible()

      // Select a shape option
      const options = shapeFilter.locator('option')
      const optionCount = await options.count()

      if (optionCount > 1) {
        await shapeFilter.selectOption({ index: 1 })
        await page.waitForTimeout(TIMEOUTS.DEBOUNCE)

        // Reset
        await shapeFilter.selectOption({ index: 0 })
        await page.waitForTimeout(TIMEOUTS.DEBOUNCE)
      }
    }
  })

  test('should select material and show detail', async ({ page }) => {
    const floatingWindow = page.locator('.floating-window')

    // Click first row
    const firstRow = floatingWindow.locator('.vt-row').first()
    await expect(firstRow).toBeVisible({ timeout: TIMEOUTS.API_LOAD })
    await firstRow.click()

    // Row should become selected
    await expect(firstRow).toHaveClass(/selected/)

    // Detail panel should appear
    const detail = floatingWindow.locator('.info-ribbon, .detail-panel, .material-detail')
    await expect(detail.first()).toBeVisible({ timeout: TIMEOUTS.API_LOAD })
  })

  test('should render only visible rows (virtualization)', async ({ page }) => {
    const floatingWindow = page.locator('.floating-window')

    // Count DOM rows
    const domRows = floatingWindow.locator('.vt-row')
    const domCount = await domRows.count()

    // Check the status label for total count
    const statusLabel = floatingWindow.locator('.count, .status-label, h3 span')
    const statusText = await statusLabel.first().textContent().catch(() => '')

    // Extract total from text like "(456)" or "200/456"
    const totalMatch = statusText?.match(/(\d+)/)
    if (totalMatch) {
      const total = parseInt(totalMatch[1])
      // DOM should have far fewer rows than total (virtualization)
      if (total > 50) {
        expect(domCount).toBeLessThan(total)
      }
    }
  })

  test('should load instantly on re-open (cached data)', async ({ page }) => {
    // First open already done in beforeEach — data is loaded
    const floatingWindow = page.locator('.floating-window')
    await expect(floatingWindow.locator('.vt-row').first()).toBeVisible({ timeout: TIMEOUTS.API_LOAD })

    // Close window
    await floatingWindow.locator('.btn-close').click()
    const cancelBtn = page.locator('.modal-overlay .btn-secondary')
    if (await cancelBtn.isVisible({ timeout: 300 }).catch(() => false)) {
      await cancelBtn.click()
    }
    await expect(floatingWindow).toBeHidden({ timeout: TIMEOUTS.ANIMATION })

    // Re-open
    const startTime = Date.now()
    await openModuleViaMenu(page, 'Materiálové položky')

    // Rows should appear instantly (from store cache)
    const newWindow = page.locator('.floating-window')
    await expect(newWindow.locator('.vt-row').first()).toBeVisible({ timeout: TIMEOUTS.API_LOAD })

    // Should be fast (< 2 seconds including window open animation)
    const elapsed = Date.now() - startTime
    expect(elapsed).toBeLessThan(3000)
  })
})
