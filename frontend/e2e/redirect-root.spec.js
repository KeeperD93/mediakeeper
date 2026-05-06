// Unauthenticated visit to "/" must redirect to the shared login page,
// preserving the original path in the ?redirect= query parameter.

import { test, expect } from '@playwright/test'
import { mockApi } from './_fixtures/api-mocks.js'

test.describe('Root route — unauthenticated redirect', () => {
  test('/ redirects to /login?redirect=/ when no session is present', async ({ page }) => {
    const tracker = await mockApi(page)

    await page.goto('/')
    await page.waitForURL(/\/login(\?|$)/, { timeout: 10_000 })

    const url = new URL(page.url())
    expect(url.pathname).toBe('/login')
    expect(url.searchParams.get('redirect')).toBe('/')

    await expect(page.locator('input[type="password"]')).toBeVisible()

    expect(tracker.unexpected).toEqual([])
  })
})
