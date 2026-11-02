// The server writes the month and the generated names: the page must ask for them in
// the language it shows, even when the portal's differs from the one saved on the device.

import { test, expect } from '@playwright/test'
import {
  DEFAULT_VIEWER_PROFILE,
  mockAuthenticatedPortal,
  portalLeaderboardHandlers,
} from './_fixtures/portal-auth-mocks.js'
import { LEADERBOARD } from './_fixtures/portal-leaderboard-page.js'

const ROUTE = '/api/portal/achievements/leaderboard/activity'

for (const [deviceLocale, portalLocale] of [
  ['en', 'fr'],
  ['fr', 'en'],
]) {
  test(`device in ${deviceLocale}, portal in ${portalLocale}: the ranking is asked in ${portalLocale}`, async ({
    page,
  }) => {
    await page.addInitScript(locale => {
      window.localStorage.setItem('mediakeeper_locale', locale)
    }, deviceLocale)
    await mockAuthenticatedPortal(page, {
      profile: {
        ...DEFAULT_VIEWER_PROFILE,
        language: portalLocale,
        effective_language: portalLocale,
      },
      pageHandlers: portalLeaderboardHandlers(LEADERBOARD),
    })

    const ranking = page.waitForRequest(request => new URL(request.url()).pathname === ROUTE)
    await page.goto('/portal/leaderboard')

    expect((await ranking).headers()['x-mk-locale']).toBe(portalLocale)
    await expect(page.locator('html')).toHaveAttribute('lang', portalLocale)
  })
}
