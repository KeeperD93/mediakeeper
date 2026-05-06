// Login page render smoke — desktop + mobile via Playwright projects.
//
// Verifies the unauthenticated /login page renders its core form once the
// /api/health probe answers 200 and the boot-time auth checks return 401.

import { test, expect } from '@playwright/test'
import { mockApi } from './_fixtures/api-mocks.js'

test.describe('Login page — render smoke', () => {
  test('renders the login form after backend health passes', async ({ page }) => {
    const tracker = await mockApi(page)

    await page.goto('/login')

    const usernameInput = page.locator('input[type="text"]').first()
    const passwordInput = page.locator('input[type="password"]')
    const submitButton = page.locator('button.login-submit')

    await expect(usernameInput).toBeVisible()
    await expect(passwordInput).toBeVisible()
    await expect(submitButton).toBeVisible()
    await expect(submitButton).toBeEnabled()

    await expect(page.locator('[data-test="login-version"]')).toBeVisible()
    await expect(page.locator('[data-test="login-github-link"]')).toBeVisible()

    expect(tracker.unexpected).toEqual([])
  })
})
