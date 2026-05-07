// Authenticated-Portal a11y baseline.
//
// Targets the same routes covered by portal-authenticated-smoke.spec.js
// (/portal/lists, /portal/settings#appearance, /portal/tickets) and runs
// a deliberately narrow axe pass — only the WCAG quick-win blockers
// already covered on /login (landmark-one-main, region,
// page-has-heading-one). No global axe sweep, no new dependency, no
// real backend or session: every /api/** call is intercepted by the
// strict authenticated mock layer.
//
// Also covers keyboard-only access on an authenticated route:
//   - Tab from a fresh page focuses the skip-link first.
//   - Enter on the skip-link moves focus to the #main-content element.

import { test, expect } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
import {
  mockAuthenticatedPortal,
  portalListsHandlers,
  portalSettingsHandlers,
  portalTicketsHandlers,
} from './_fixtures/portal-auth-mocks.js'

const TARGETED_RULES = ['landmark-one-main', 'region', 'page-has-heading-one']

async function forceEnglishLocale(page) {
  await page.addInitScript(() => {
    window.localStorage.setItem('mediakeeper_locale', 'en')
  })
}

async function assertSinglePortalShell(page) {
  await expect(page).not.toHaveURL(/\/login(\?|#|$)/)
  const main = page.locator('main#main-content')
  await expect(main).toBeVisible()
  await expect(page.locator('h1')).toHaveCount(1)
  await expect(page.locator('main#main-content h1')).toHaveCount(1)
}

async function runTargetedAxe(page) {
  const results = await new AxeBuilder({ page })
    .include('main#main-content')
    .withRules(TARGETED_RULES)
    .analyze()

  expect(results.violations, JSON.stringify(results.violations, null, 2)).toEqual([])
}

test.describe('Portal authenticated — targeted a11y baseline', () => {
  test('/portal/lists exposes the expected landmarks and single h1', async ({ page }) => {
    await forceEnglishLocale(page)
    const tracker = await mockAuthenticatedPortal(page, {
      pageHandlers: portalListsHandlers(),
    })

    await page.goto('/portal/lists')

    await expect(page.getByRole('heading', { level: 1, name: 'My lists' })).toBeVisible()
    await assertSinglePortalShell(page)
    await runTargetedAxe(page)

    expect(tracker.unexpected).toEqual([])
  })

  test('/portal/settings#appearance exposes the expected landmarks and single h1', async ({
    page,
  }) => {
    await forceEnglishLocale(page)
    const tracker = await mockAuthenticatedPortal(page, {
      pageHandlers: portalSettingsHandlers(),
    })

    await page.goto('/portal/settings#appearance')

    await expect(page.getByRole('heading', { level: 1, name: 'Settings' })).toBeVisible()
    await expect(page.getByRole('tab', { name: 'Appearance' })).toBeVisible()
    await assertSinglePortalShell(page)
    await runTargetedAxe(page)

    expect(tracker.unexpected).toEqual([])
  })

  test('/portal/tickets exposes the expected landmarks and single h1', async ({ page }) => {
    await forceEnglishLocale(page)
    const tracker = await mockAuthenticatedPortal(page, {
      pageHandlers: portalTicketsHandlers(),
    })

    await page.goto('/portal/tickets')

    await expect(page.getByRole('heading', { level: 1, name: 'Issues' })).toBeVisible()
    await assertSinglePortalShell(page)
    await runTargetedAxe(page)

    expect(tracker.unexpected).toEqual([])
  })
})

test.describe('Portal authenticated — keyboard skip-link', () => {
  test('Tab focuses the skip-link, Enter jumps focus into #main-content', async ({ page }) => {
    await forceEnglishLocale(page)
    const tracker = await mockAuthenticatedPortal(page, {
      pageHandlers: portalListsHandlers(),
    })

    await page.goto('/portal/lists')
    await expect(page.getByRole('heading', { level: 1, name: 'My lists' })).toBeVisible()

    // Drop any focus that may have been set by autofocus / scripts so Tab
    // starts from the document root.
    await page.evaluate(() => {
      if (document.activeElement instanceof HTMLElement) document.activeElement.blur()
    })

    await page.keyboard.press('Tab')

    const skipLink = page.locator('a.mk-skip-link')
    await expect(skipLink).toBeFocused()

    await page.keyboard.press('Enter')

    await expect(page).toHaveURL(/#main-content$/)

    const mainFocused = await page.evaluate(() => {
      const main = document.getElementById('main-content')
      return !!main && (document.activeElement === main || main.contains(document.activeElement))
    })
    expect(mainFocused).toBe(true)

    expect(tracker.unexpected).toEqual([])
  })
})
