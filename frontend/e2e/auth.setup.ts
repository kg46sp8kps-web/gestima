import { test as setup } from '@playwright/test'

const AUTH_FILE = 'e2e/.auth/user.json'

setup('authenticate', async ({ page }) => {
  await page.goto('/login')
  await page.waitForSelector('[data-testid="username-input"]', { state: 'visible', timeout: 10000 })

  await page.fill('[data-testid="username-input"]', 'demo')
  await page.fill('[data-testid="password-input"]', 'demo123')
  await page.click('[data-testid="login-button"]')

  await page.waitForSelector('.menu-btn', { state: 'visible', timeout: 15000 })

  await page.context().storageState({ path: AUTH_FILE })
})
