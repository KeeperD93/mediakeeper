// Logout feedback — arriving on /login?logged_out=1 must surface a non-
// intrusive status banner confirming the sign-out, while keeping the
// login form rendered and untouched (no redirect, no login-error).

import { test, expect } from '@playwright/test'
import { mockApi } from './_fixtures/api-mocks.js'

test.describe('Login — logged-out feedback', () => {
  test('shows the logged-out banner and preserves the form', async ({ page }) => {
    const tracker = await mockApi(page)

    await page.goto('/login?logged_out=1')

    const banner = page.locator('[data-test="login-logged-out"]')
    await expect(banner).toBeVisible()
    await expect(banner).toHaveAttribute('role', 'status')

    await expect(page.locator('input[type="password"]')).toBeVisible()
    await expect(page.locator('button.login-submit')).toBeVisible()
    await expect(page.locator('.login-error')).toHaveCount(0)

    expect(new URL(page.url()).pathname).toBe('/login')

    expect(tracker.unexpected).toEqual([])
  })
})
