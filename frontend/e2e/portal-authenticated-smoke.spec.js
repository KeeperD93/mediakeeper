// Authenticated-Portal smoke baseline.
//
// Drives /portal/lists, /portal/settings#appearance, and /portal/tickets
// with a fully fictional viewer profile served by a strict mock layer
// (see _fixtures/portal-auth-mocks.js). No real backend, no real session,
// no real account — every /api/** call is either mocked or fails the test
// via the strict catch-all in api-mocks.js.
//
// What we cover:
//   - Each route renders past the auth guard (no /login redirect).
//   - The shared <main id="main-content"> shell mounts.
//   - Page-level title / empty-state copy is correct in English.
//   - Mobile project: bottom nav surfaces the "Lists" tab.
//   - Desktop project: page stays readable without depending on the
//     bottom nav (which is hidden ≥768px).
//
// We deliberately skip every interactive write path (creating a list,
// submitting a ticket, saving settings) — those belong to scoped tests
// behind their own fixtures.

import { test, expect } from '@playwright/test'
import {
  mockAuthenticatedPortal,
  portalListsHandlers,
  portalSettingsHandlers,
  portalTicketsHandlers,
} from './_fixtures/portal-auth-mocks.js'

async function forceEnglishLocale(page) {
  await page.addInitScript(() => {
    window.localStorage.setItem('mediakeeper_locale', 'en')
  })
}

test.describe('Portal authenticated smoke — viewer profile, empty state', () => {
  test('/portal/lists renders the empty "My lists" page', async ({ page }) => {
    await forceEnglishLocale(page)
    const tracker = await mockAuthenticatedPortal(page, {
      pageHandlers: portalListsHandlers(),
    })

    await page.goto('/portal/lists')

    await expect(page).toHaveURL(/\/portal\/lists$/)
    await expect(page.locator('main#main-content')).toBeVisible()
    await expect(page.getByRole('heading', { level: 1, name: 'My lists' })).toBeVisible()

    expect(tracker.unexpected).toEqual([])
  })

  test('/portal/settings#appearance keeps the hash and renders the tab', async ({ page }) => {
    await forceEnglishLocale(page)
    const tracker = await mockAuthenticatedPortal(page, {
      pageHandlers: portalSettingsHandlers(),
    })

    await page.goto('/portal/settings#appearance')

    await expect(page).toHaveURL(/\/portal\/settings#appearance$/)
    await expect(page.locator('main#main-content')).toBeVisible()
    await expect(page.getByRole('heading', { level: 1, name: 'Settings' })).toBeVisible()
    await expect(page.getByRole('tab', { name: 'Appearance' })).toBeVisible()
    expect(new URL(page.url()).hash).toBe('#appearance')

    expect(tracker.unexpected).toEqual([])
  })

  test('/portal/tickets renders the empty issues list', async ({ page }) => {
    await forceEnglishLocale(page)
    const tracker = await mockAuthenticatedPortal(page, {
      pageHandlers: portalTicketsHandlers(),
    })

    await page.goto('/portal/tickets')

    await expect(page).toHaveURL(/\/portal\/tickets$/)
    await expect(page.locator('main#main-content')).toBeVisible()
    await expect(page.getByRole('heading', { level: 1, name: 'Issues' })).toBeVisible()
    await expect(page.getByText('No tickets yet')).toBeVisible()

    expect(tracker.unexpected).toEqual([])
  })
})

test.describe('Portal authenticated smoke — responsive shell', () => {
  test('mobile bottom nav exposes the Lists tab', async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== 'chromium-mobile', 'mobile-only viewport check')
    await forceEnglishLocale(page)
    const tracker = await mockAuthenticatedPortal(page, {
      pageHandlers: portalListsHandlers(),
    })

    await page.goto('/portal/lists')

    const bottomNav = page.locator('nav.pt-bottom-nav')
    await expect(bottomNav).toBeVisible()
    await expect(bottomNav.getByRole('button', { name: 'Lists' })).toBeVisible()

    expect(tracker.unexpected).toEqual([])
  })

  test('desktop renders the page shell without relying on the bottom nav', async ({
    page,
  }, testInfo) => {
    test.skip(testInfo.project.name !== 'chromium-desktop', 'desktop-only viewport check')
    await forceEnglishLocale(page)
    const tracker = await mockAuthenticatedPortal(page, {
      pageHandlers: portalListsHandlers(),
    })

    await page.goto('/portal/lists')

    await expect(page.locator('main#main-content')).toBeVisible()
    await expect(page.getByRole('heading', { level: 1, name: 'My lists' })).toBeVisible()

    expect(tracker.unexpected).toEqual([])
  })
})
