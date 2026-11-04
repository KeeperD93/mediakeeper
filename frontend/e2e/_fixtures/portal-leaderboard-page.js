// The leaderboard page with fictional players: the longest names and titles, and
// the largest totals, so a layout test meets the worst case on every row.

import { expect } from '@playwright/test'
import {
  DEFAULT_VIEWER_PROFILE,
  mockAuthenticatedPortal,
  portalLeaderboardHandlers,
} from './portal-auth-mocks.js'

const LONG_NAME = 'Alice-with-a-rather-long-display-name'
const LONGEST_LEVEL_TITLE = 'spectator'
const LONGEST_CHOSEN_TITLE = 'portal.titles.supremeCollector'

function buildEntry(index) {
  return {
    rank: index + 1,
    user_id: 1000 + index,
    display_name: index % 2 ? `Player ${index}` : LONG_NAME,
    avatar_url: null,
    level: 50,
    tier: 'gold',
    title_key: LONGEST_LEVEL_TITLE,
    period_xp: 1234567 - index * 1000,
    selected_title: LONGEST_CHOSEN_TITLE,
    title_tier: 6,
    is_current_user: false,
    movement: 2,
    trophies_won: index % 2 ? 0 : 123,
  }
}

export const LEADERBOARD = {
  items: Array.from({ length: 20 }, (_, index) => buildEntry(index)),
  viewer_rank: 120,
  viewer_entry: { ...buildEntry(119), is_current_user: true },
  stats: {
    period_label: 'Novembre 2026',
    total_players: 1234,
    total_xp: 1234567,
    total_trophies: 1234,
    days_remaining: 28,
    days_in_month: 30,
    my_xp: 1234,
    my_delta_week: 123,
    projected_end_rank: 12,
  },
}

export function viewerInList(viewerIndex) {
  return {
    ...LEADERBOARD,
    items: LEADERBOARD.items.map((entry, index) => ({
      ...entry,
      is_current_user: index === viewerIndex,
    })),
    viewer_rank: null,
    viewer_entry: null,
  }
}

/**
 * On rows with trophies, the room above the digits of the XP and under the trophy badge:
 * what the eye reads, so from the ink of the text and not from its box.
 */
export function roomAroundFigures(page, rowSelector, xpSelector) {
  return page.locator(rowSelector).evaluateAll((rows, xp) => {
    const canvas = document.createElement('canvas').getContext('2d')
    return rows
      .filter(row => row.querySelector('.lb-trophies'))
      .map(row => {
        const element = row.querySelector(xp)
        const style = getComputedStyle(element)
        canvas.font = `${style.fontWeight} ${style.fontSize} ${style.fontFamily}`
        const metrics = canvas.measureText(element.textContent.trim())
        const text = document.createRange()
        text.selectNodeContents(element)
        const ink =
          text.getBoundingClientRect().top +
          metrics.fontBoundingBoxAscent -
          metrics.actualBoundingBoxAscent
        const box = row.getBoundingClientRect()
        const badge = row.querySelector('.lb-trophies').getBoundingClientRect()
        return { above: ink - box.top, under: box.bottom - badge.bottom }
      })
  }, xpSelector)
}

export async function openLeaderboard(page, width, body) {
  await page.setViewportSize({ width, height: 800 })
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await page.addInitScript(() => {
    window.localStorage.setItem('mediakeeper_locale', 'fr')
  })
  const tracker = await mockAuthenticatedPortal(page, {
    profile: { ...DEFAULT_VIEWER_PROFILE, language: 'fr' },
    pageHandlers: portalLeaderboardHandlers(body),
  })
  await page.goto('/portal/leaderboard')
  await expect(page.locator('.lb-hero')).toBeVisible()
  return tracker
}
