// Ranking of "My profile": however narrow its column, each row keeps room for the
// name and the level, and the trophies stay under the XP, inside the card.

import { test, expect } from '@playwright/test'
import { jsonResponse } from './_fixtures/api-mocks.js'
import {
  DEFAULT_VIEWER_PROFILE,
  mockAuthenticatedPortal,
  portalSettingsHandlers,
} from './_fixtures/portal-auth-mocks.js'

const MIN_NAME_WIDTH = 100

const LEADERBOARD = Array.from({ length: 16 }, (_, index) => ({
  rank: index + 1,
  user_id: 1000 + index,
  display_name: `Player ${index}`,
  avatar_url: null,
  level: 50 - index,
  tier: 'gold',
  title_key: 'spectator',
  period_xp: 12345 - index,
  selected_title: 'portal.titles.supremeCollector',
  title_tier: 6,
  is_current_user: index === 5,
  movement: 2,
  trophies_won: index % 2 ? 0 : 123,
}))

async function expectRowsReadable(page, width) {
  await page.setViewportSize({ width, height: 800 })
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await page.addInitScript(() => {
    window.localStorage.setItem('mediakeeper_locale', 'fr')
  })
  const profile = { ...DEFAULT_VIEWER_PROFILE, language: 'fr' }
  const tracker = await mockAuthenticatedPortal(page, {
    profile,
    pageHandlers: portalSettingsHandlers({ profile }),
    extraOverrides: [
      {
        name: 'portal-catalog-profile-full-ranking',
        match: url => url.pathname === '/api/portal/catalog/profile-full',
        handler: jsonResponse({
          stats: {},
          ranking: {
            position: 6,
            total: 16,
            percentile: 37,
            movement: 2,
            leaderboard: LEADERBOARD,
          },
          title_key: 'spectator',
          rank_tier: 'gold',
          recent_watches: [],
          my_requests: [],
          next_to_finish: [],
        }),
      },
    ],
  })

  await page.goto('/portal/me')
  await expect(page.locator('.gc-lb-box .gc-lb-row')).toHaveCount(LEADERBOARD.length)
  await expect(page.locator('.gc-lb-box .gc-lb-tier').first()).toContainText('Niveau 50')

  const rows = await page.locator('.gc-lb-box .gc-lb-row').evaluateAll(elements =>
    elements.map(row => {
      const box = selector => row.querySelector(selector).getBoundingClientRect()
      const card = row.closest('.gc-lb-box').getBoundingClientRect()
      return {
        nameWidth: box('.gc-lb-info').width,
        moveBottom: box('.gc-lb-move').bottom,
        xpTop: box('.gc-lb-v').top,
        xpBottom: box('.gc-lb-v').bottom,
        xpRight: box('.gc-lb-v').right,
        cardRight: card.right,
        cardLeft: card.left,
        trophies: row.querySelector('.lb-trophies')?.getBoundingClientRect().toJSON() ?? null,
      }
    }),
  )
  for (const row of rows) {
    expect(row.nameWidth).toBeGreaterThanOrEqual(MIN_NAME_WIDTH)
    expect(row.xpTop).toBeLessThan(row.moveBottom)
    expect(row.xpRight).toBeLessThanOrEqual(row.cardRight)
    if (row.trophies) {
      // Under the XP, against the same edge, inside the card.
      expect(row.trophies.top).toBeGreaterThanOrEqual(row.xpBottom - 1)
      expect(Math.abs(row.trophies.right - row.xpRight)).toBeLessThanOrEqual(1)
      expect(row.trophies.left).toBeGreaterThanOrEqual(row.cardLeft)
    }
  }
  expect(rows.filter(row => row.trophies)).toHaveLength(8)
  expect(tracker.unexpected).toEqual([])
}

test.describe('Ranking of My profile on a large screen', () => {
  test.skip(({ isMobile }) => isMobile, 'large screen layout only')

  for (const width of [1024, 1280, 1366, 1600, 1920]) {
    test(`keeps names and levels readable at ${width}px`, async ({ page }) => {
      await expectRowsReadable(page, width)
    })
  }
})

test.describe('Ranking of My profile on a phone', () => {
  test.skip(({ isMobile }) => !isMobile, 'phone layout only')

  for (const width of [320, 375, 430]) {
    test(`keeps names and levels readable at ${width}px`, async ({ page }) => {
      await expectRowsReadable(page, width)
    })
  }
})
