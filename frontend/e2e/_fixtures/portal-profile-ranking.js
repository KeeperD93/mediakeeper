// "My profile" with a ranking of its own on each period, fictional players.

import { expect } from '@playwright/test'
import { jsonResponse } from './api-mocks.js'
import {
  DEFAULT_VIEWER_PROFILE,
  LEADERBOARD_ROUTE,
  mockAuthenticatedPortal,
  portalSettingsHandlers,
} from './portal-auth-mocks.js'

const PROFILE_ROUTE = '/api/portal/catalog/profile-full'
const TOP = 15

const player = (index, xp, extra = {}) => ({
  rank: index + 1,
  user_id: 1000 + index,
  display_name: `Player ${index}`,
  avatar_url: null,
  level: 50 - index,
  tier: 'gold',
  title_key: 'spectator',
  period_xp: xp - index,
  selected_title: null,
  title_tier: 0,
  is_current_user: false,
  movement: 2,
  trophies_won: 0,
  ...extra,
})

const top = (xp, extra) => Array.from({ length: TOP }, (_, index) => player(index, xp, extra))

const VIEWER = player(41, 99, { display_name: 'Alice', is_current_user: true })

const board = (xp, extra, viewer = null) => ({
  items: top(xp, extra),
  viewer_rank: viewer?.rank ?? null,
  viewer_entry: viewer,
  stats: null,
})

export const MONTH = top(33333)

export const BY_PERIOD = {
  today: board(111, undefined, VIEWER),
  week: board(2222),
  all: board(444444, { movement: null }, { ...VIEWER, movement: null }),
}

export const LABELS = { today: "Aujourd'hui", week: 'Semaine', month: 'Mois', all: 'Tout temps' }

export const card = page => page.locator('.gc-lb-box--tabs')
export const menu = page => card(page).locator('select')
export const tab = (page, period) => card(page).getByRole('tab', { name: LABELS[period] })
export const firstXp = page => card(page).locator('.gc-lb-v').first()

/**
 * Waits for the web fonts the page is laid out with. Until they arrive, the figures are
 * drawn in a fallback font of another width, which moves the room left for the names.
 */
export const fontsLoaded = page =>
  page.evaluate(async () => {
    // Laying the page out starts the loads of the fonts it uses, so `ready` waits for them.
    document.body.getBoundingClientRect()
    await document.fonts.ready
  })

/** Opens "My profile" and returns the list of the rankings it asked for. */
export async function openProfile(
  page,
  { width, locale = 'fr', byPeriod = BY_PERIOD, month = MONTH, delays = {} } = {},
) {
  await page.setViewportSize({ width, height: 800 })
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await page.addInitScript(language => {
    window.localStorage.setItem('mediakeeper_locale', language)
  }, locale)
  const profile = { ...DEFAULT_VIEWER_PROFILE, language: locale }
  const asked = []
  const tracker = await mockAuthenticatedPortal(page, {
    profile,
    pageHandlers: portalSettingsHandlers({ profile }),
    extraOverrides: [
      {
        name: 'portal-catalog-profile-full-ranking',
        match: url => url.pathname === PROFILE_ROUTE,
        handler: jsonResponse({
          stats: {},
          ranking: { position: 6, total: TOP, percentile: 37, movement: 2, leaderboard: month },
          title_key: 'spectator',
          rank_tier: 'gold',
          recent_watches: [],
          my_requests: [],
          next_to_finish: [],
        }),
      },
      {
        name: 'portal-leaderboard-activity',
        match: url => url.pathname === LEADERBOARD_ROUTE,
        handler: async route => {
          const url = new URL(route.request().url())
          const period = url.searchParams.get('period')
          asked.push(`${period}:${url.searchParams.get('limit')}`)
          if (delays[period]) await new Promise(resolve => setTimeout(resolve, delays[period]))
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify(byPeriod[period]),
          })
        },
      },
    ],
  })
  await page.goto('/portal/me')
  await expect(card(page)).toBeVisible()
  return { asked, tracker }
}
