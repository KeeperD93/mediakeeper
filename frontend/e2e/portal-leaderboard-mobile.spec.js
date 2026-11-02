// Leaderboard on a phone: the page stays as wide as the screen, whatever the
// names and totals of the fictional players, no figure is cut off, and the
// longest level title next to the longest chosen title stays inside its card.

import { test, expect } from '@playwright/test'
import {
  DEFAULT_VIEWER_PROFILE,
  mockAuthenticatedPortal,
  portalLeaderboardHandlers,
} from './_fixtures/portal-auth-mocks.js'

const LONG_NAME = 'Alice-with-a-rather-long-display-name'
const LONGEST_LEVEL_TITLE = 'spectator'
const LONGEST_CHOSEN_TITLE = 'portal.titles.supremeCollector'

// Each card of the page, with the titles it must keep inside.
const TITLES_BY_CARD = {
  '.lb-hero': '.lb-hero-meta',
  '.pt-lb-podium-card': '.pt-lb-podium-meta',
  '.lb-top-row': '.lb-top-row-title',
  '.gc-lb-row': '.gc-lb-tier',
}

// Every figure the page must keep inside the screen.
const FIGURES = [
  '.lb-hero-xp-unit',
  '.lb-hero-lead',
  '.lb-stats-chip',
  '.pt-lb-podium-xp',
  '.lb-my-rank-rank',
  '.lb-top-row-xp',
  '.gc-lb-v',
]

function buildEntry(index) {
  return {
    rank: index + 1,
    user_id: 1000 + index,
    display_name: index % 2 ? `Player ${index}` : LONG_NAME,
    avatar_url: null,
    level: 50,
    tier: 'gold',
    title_key: LONGEST_LEVEL_TITLE,
    month_xp: 1234567 - index * 1000,
    selected_title: LONGEST_CHOSEN_TITLE,
    title_tier: 6,
    is_current_user: false,
    movement: 2,
  }
}

const LEADERBOARD = {
  items: Array.from({ length: 20 }, (_, index) => buildEntry(index)),
  viewer_rank: 120,
  viewer_entry: { ...buildEntry(119), is_current_user: true },
  stats: {
    month_label: 'Novembre 2026',
    total_players: 1234,
    total_xp_month: 1234567,
    total_trophies_month: 1234,
    days_remaining: 28,
    my_xp_month: 1234,
    my_delta_week: 123,
    projected_end_rank: 12,
  },
}

test.describe('Portal leaderboard on a phone', () => {
  test.skip(({ isMobile }) => !isMobile, 'phone layout only')

  for (const width of [320, 375, 430, 767]) {
    test(`fits a ${width}px screen, every figure included`, async ({ page }) => {
      await page.setViewportSize({ width, height: 800 })
      await page.emulateMedia({ reducedMotion: 'reduce' })
      await page.addInitScript(() => {
        window.localStorage.setItem('mediakeeper_locale', 'fr')
      })
      const tracker = await mockAuthenticatedPortal(page, {
        profile: { ...DEFAULT_VIEWER_PROFILE, language: 'fr' },
        pageHandlers: portalLeaderboardHandlers(LEADERBOARD),
      })

      await page.goto('/portal/leaderboard')
      await expect(page.locator('.lb-hero')).toBeVisible()

      const overflowing = await page.evaluate(selectors => {
        const screenWidth = document.documentElement.clientWidth
        const root = document.querySelector('.pt-leaderboard')
        const out = root.getBoundingClientRect().right > screenWidth ? ['.pt-leaderboard'] : []
        for (const selector of selectors) {
          const elements = [...root.querySelectorAll(selector)]
          if (!elements.length) out.push(`${selector} is missing`)
          if (elements.some(el => el.getBoundingClientRect().right > screenWidth)) {
            out.push(selector)
          }
        }
        return out
      }, FIGURES)

      const titlesOutOfCard = await page.evaluate(titlesByCard => {
        const out = []
        for (const [cardSelector, titleSelector] of Object.entries(titlesByCard)) {
          for (const card of document.querySelectorAll(`.pt-leaderboard ${cardSelector}`)) {
            const box = card.getBoundingClientRect()
            const range = document.createRange()
            range.selectNodeContents(card.querySelector(titleSelector))
            const lines = [...range.getClientRects()]
            if (lines.some(line => line.right > box.right || line.left < box.left)) {
              out.push(titleSelector)
            }
          }
        }
        return out
      }, TITLES_BY_CARD)

      expect(overflowing).toEqual([])
      expect(titlesOutOfCard).toEqual([])
      expect(tracker.unexpected).toEqual([])
    })
  }
})
