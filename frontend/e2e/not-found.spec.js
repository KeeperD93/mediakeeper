// Unknown routes must render the standalone 404 view, not redirect to /login.
// Covers both the admin catch-all and the /portal/* catch-all so the silent
// redirect-to-login regression flagged by the UX audit can never come back.

import { test, expect } from '@playwright/test'
import { mockApi } from './_fixtures/api-mocks.js'

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

test.describe('Catch-all 404 — admin scope', () => {
  test('/abcdef-route-inexistante renders the 404 view, not /login', async ({ page }) => {
    const tracker = await mockApi(page)

    await page.goto('/abcdef-route-inexistante')
    await expect(page.locator('[data-test="not-found-page"]')).toBeVisible()

    const url = new URL(page.url())
    expect(url.pathname).toBe('/abcdef-route-inexistante')

    const main = page.locator('main#main-content')
    await expect(main).toBeVisible()
    const heading = page.locator('h1')
    await expect(heading).toHaveCount(1)
    await expect(heading).toBeVisible()
    await expect(page.locator('[data-test="not-found-cta-home"]')).toBeVisible()
    await expect(page.locator('[data-test="not-found-cta-portal"]')).toHaveCount(0)

    expect(page.url()).not.toMatch(/\/login/)

    const headingText = (await heading.textContent())?.trim() ?? ''
    expect(headingText.length).toBeGreaterThan(0)
    await expect(page).toHaveTitle(new RegExp(`^MediaKeeper · ${escapeRegExp(headingText)}$`))

    expect(tracker.unexpected).toEqual([])
  })
})

test.describe('Catch-all 404 — portal scope', () => {
  test('/portal/abcdef-inexistante renders the 404 view with the portal CTA', async ({ page }) => {
    const tracker = await mockApi(page)

    await page.goto('/portal/abcdef-inexistante')
    await expect(page.locator('[data-test="not-found-page"]')).toBeVisible()

    const url = new URL(page.url())
    expect(url.pathname).toBe('/portal/abcdef-inexistante')

    await expect(page.locator('main#main-content')).toBeVisible()
    const heading = page.locator('h1')
    await expect(heading).toHaveCount(1)
    await expect(heading).toBeVisible()
    await expect(page.locator('[data-test="not-found-cta-portal"]')).toBeVisible()
    await expect(page.locator('[data-test="not-found-cta-home"]')).toHaveCount(0)

    expect(page.url()).not.toMatch(/\/login/)

    const headingText = (await heading.textContent())?.trim() ?? ''
    expect(headingText.length).toBeGreaterThan(0)
    await expect(page).toHaveTitle(new RegExp(`^MediaKeeper · ${escapeRegExp(headingText)}$`))

    expect(tracker.unexpected).toEqual([])
  })
})
