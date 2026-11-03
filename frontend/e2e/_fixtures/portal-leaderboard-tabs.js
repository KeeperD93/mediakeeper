// The leaderboard page with a ranking of its own on each tab, fictional players.

import { expect } from '@playwright/test'
import {
  DEFAULT_VIEWER_PROFILE,
  LEADERBOARD_ROUTE,
  mockAuthenticatedPortal,
} from './portal-auth-mocks.js'
import { LEADERBOARD } from './portal-leaderboard-page.js'

const withLeaderXp = (xp, stats, movement = 2) => ({
  ...LEADERBOARD,
  items: LEADERBOARD.items.map((entry, index) => ({
    ...entry,
    period_xp: xp - index,
    movement,
  })),
  stats: { ...LEADERBOARD.stats, total_xp: xp * 10, ...stats },
})

const SHORT_PERIOD = { days_remaining: null, my_delta_week: null, projected_end_rank: null }

export const BY_PERIOD = {
  today: withLeaderXp(111, { period_label: 'Lundi 2 novembre', ...SHORT_PERIOD }),
  week: withLeaderXp(2222, { period_label: 'Du 2 au 8 novembre', ...SHORT_PERIOD }),
  month: withLeaderXp(33333, { period_label: 'Novembre 2026' }),
  all: withLeaderXp(444444, { period_label: 'Depuis le début', ...SHORT_PERIOD }, null),
}

export const LABELS = { today: "Aujourd'hui", week: 'Semaine', month: 'Mois', all: 'Tout temps' }

export const tab = (page, period) => page.getByRole('tab', { name: LABELS[period] })

/** Opens the page on the month and returns the list of the rankings it asked for. */
export async function openTabs(
  page,
  { width = 1280, byPeriod = BY_PERIOD, delays = {}, reducedMotion = 'reduce' } = {},
) {
  await page.setViewportSize({ width, height: 800 })
  await page.emulateMedia({ reducedMotion })
  await page.addInitScript(() => {
    window.localStorage.setItem('mediakeeper_locale', 'fr')
  })
  const asked = []
  await mockAuthenticatedPortal(page, {
    profile: { ...DEFAULT_VIEWER_PROFILE, language: 'fr' },
    pageHandlers: [
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
  await page.goto('/portal/leaderboard')
  await expect(tab(page, 'month')).toHaveAttribute('aria-selected', 'true')
  return asked
}
