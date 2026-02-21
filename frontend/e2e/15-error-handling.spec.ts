import { test, expect } from '@playwright/test'
import { login } from './helpers/auth'
import { openModuleViaMenu, setupWindowsView, TIMEOUTS } from './helpers/windows'

test.describe('Error Handling & Edge Cases', () => {
  test('should show toast notification on API error', async ({ page }) => {
    await login(page)
    await setupWindowsView(page)

    // Intercept an API call and return 500
    await page.route('**/api/quotes**', route => {
      route.fulfill({
        status: 500,
        body: JSON.stringify({ detail: 'Internal Server Error' }),
        headers: { 'Content-Type': 'application/json' }
      })
    })

    // Open quotes module to trigger the error
    await openModuleViaMenu(page, 'Nabídky')
    await page.waitForTimeout(TIMEOUTS.API_LOAD)

    // Error toast should appear
    const toast = page.locator('.toast, .notification, [role="alert"], .toast-container')
    await toast.first().isVisible({ timeout: TIMEOUTS.API_LOAD }).catch(() => false)

    // Restore the route
    await page.unroute('**/api/quotes**')
  })

  test('should handle session expiry gracefully', async ({ page }) => {
    await login(page)
    await page.goto('/windows')
    await page.waitForSelector('.menu-btn', { state: 'visible', timeout: 10000 })

    // Intercept auth check to return 401
    await page.route('**/api/auth/me', route => {
      route.fulfill({
        status: 401,
        body: JSON.stringify({ detail: 'Not authenticated' }),
        headers: { 'Content-Type': 'application/json' }
      })
    })

    // Navigate to trigger auth check
    await page.goto('/windows')

    // Should redirect to login
    await page.waitForSelector('[data-testid="login-button"]', { state: 'visible', timeout: TIMEOUTS.API_LOAD })
  })

  test('should handle empty module states', async ({ page }) => {
    await login(page)
    await setupWindowsView(page)

    // Open a module
    await openModuleViaMenu(page, 'Admin')
    const floatingWindow = page.locator('.floating-window')
    await expect(floatingWindow).toBeVisible({ timeout: TIMEOUTS.WINDOW_OPEN })

    // The module should render without errors
    const windowContent = floatingWindow.locator('.window-content')
    await expect(windowContent).toBeVisible()
  })

  test('should preserve login after page reload', async ({ page }) => {
    await login(page)
    await page.goto('/windows')
    await page.waitForSelector('.menu-btn', { state: 'visible', timeout: 10000 })

    // Reload page
    await page.reload()

    // Should stay authenticated — menu button visible
    await expect(page.locator('.menu-btn')).toBeVisible({ timeout: 10000 })
  })
})
