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
    month_xp: 1234567 - index * 1000,
    selected_title: LONGEST_CHOSEN_TITLE,
    title_tier: 6,
    is_current_user: false,
    movement: 2,
  }
}

export const LEADERBOARD = {
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
