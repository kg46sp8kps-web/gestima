import { test, expect } from '@playwright/test'

// Login tests need a clean browser (no storageState)
test.use({ storageState: { cookies: [], origins: [] } })

test.describe('Login Flow', () => {
  test('should display login page', async ({ page }) => {
    await page.goto('/login')

    await expect(page.locator('[data-testid="username-input"]')).toBeVisible()
    await expect(page.locator('[data-testid="password-input"]')).toBeVisible()
    await expect(page.locator('[data-testid="login-button"]')).toBeVisible()
  })

  test('should show error on invalid credentials', async ({ page }) => {
    await page.goto('/login')

    await page.fill('[data-testid="username-input"]', 'invalid')
    await page.fill('[data-testid="password-input"]', 'invalid')
    await page.click('[data-testid="login-button"]')

    // Should show error message
    const errorMsg = page.locator('.error-message, .toast, [role="alert"]')
    await expect(errorMsg.first()).toBeVisible({ timeout: 5000 })
  })

  test('should successfully login with valid credentials', async ({ page }) => {
    await page.goto('/login')

    await page.fill('[data-testid="username-input"]', 'demo')
    await page.fill('[data-testid="password-input"]', 'demo123')
    await page.click('[data-testid="login-button"]')

    // Should redirect and show menu button
    await expect(page.locator('.menu-btn')).toBeVisible({ timeout: 15000 })
  })

  test('should successfully logout', async ({ page }) => {
    // Login first
    await page.goto('/login')
    await page.fill('[data-testid="username-input"]', 'demo')
    await page.fill('[data-testid="password-input"]', 'demo123')
    await page.click('[data-testid="login-button"]')
    await page.waitForSelector('.menu-btn', { state: 'visible', timeout: 15000 })

    // Logout
    await page.click('.menu-btn')
    await page.waitForSelector('.menu-drawer', { state: 'visible' })
    await page.click('.logout-btn')

    // Should show login page
    await expect(page.locator('[data-testid="login-button"]')).toBeVisible({ timeout: 10000 })
  })

  test('should redirect to login when accessing protected route unauthenticated', async ({ page }) => {
    await page.goto('/windows')

    // Should redirect to login
    await expect(page.locator('[data-testid="login-button"]')).toBeVisible({ timeout: 10000 })
  })
})
