// Submitting the login form with empty fields must surface the
// client-side validation error without sending a login request.

import { test, expect } from '@playwright/test'
import { mockApi } from './_fixtures/api-mocks.js'

test.describe('Login validation — empty fields', () => {
  test('shows the inline error and never calls /api/auth/portal-login', async ({ page }) => {
    let loginAttempts = 0

    const tracker = await mockApi(page, {
      overrides: [
        {
          name: 'portal-login-spy',
          match: url => url.pathname === '/api/auth/portal-login',
          handler: route => {
            loginAttempts += 1
            return route.fulfill({
              status: 401,
              contentType: 'application/json',
              body: JSON.stringify({ detail: 'unexpected — should not be called' }),
            })
          },
        },
      ],
    })

    await page.goto('/login')

    const submitButton = page.locator('button.login-submit')
    await expect(submitButton).toBeVisible()
    await submitButton.click()

    await expect(page.locator('.login-error')).toBeVisible()

    // Give the network layer a beat: if a request had been queued, it would
    // resolve well within this window. We assert no login attempt was fired.
    await page.waitForTimeout(300)
    expect(loginAttempts).toBe(0)
    expect(tracker.unexpected).toEqual([])
  })
})
