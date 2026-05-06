// /portal/login is a router-level redirect to the shared /login page,
// preserving /portal as the post-login destination. The redirect is purely
// client-side; no backend call should be required to reach /login.

import { test, expect } from '@playwright/test'
import { mockApi } from './_fixtures/api-mocks.js'

test.describe('Portal login alias — shared login redirect', () => {
  test('/portal/login redirects to /login?redirect=/portal', async ({ page }) => {
    const tracker = await mockApi(page)

    await page.goto('/portal/login')
    await page.waitForURL(/\/login\?/, { timeout: 10_000 })

    const url = new URL(page.url())
    expect(url.pathname).toBe('/login')
    expect(url.searchParams.get('redirect')).toBe('/portal')

    await expect(page.locator('input[type="password"]')).toBeVisible()

    expect(tracker.unexpected).toEqual([])
  })
})
