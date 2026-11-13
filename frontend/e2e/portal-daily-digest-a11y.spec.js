// Daily digest window, a11y: it opens by itself over a portal page, with fictional
// content in every section, and passes a full axe pass in both of its views.

import { test, expect } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
import { jsonResponse } from './_fixtures/api-mocks.js'
import { mockAuthenticatedPortal, portalListsHandlers } from './_fixtures/portal-auth-mocks.js'

const hoursAgo = hours => new Date(Date.now() - hours * 3600e3).toISOString()

const entry = (rank, name, extra = {}) => ({
  rank,
  user_id: 1000 + rank,
  display_name: name,
  avatar_url: null,
  avatar_effect: null,
  level: 20 + rank,
  tier: 'platinum',
  title_key: 'passionate',
  period_xp: 1300 - rank * 100,
  movement: 0,
  trophies_won: 0,
  is_current_user: false,
  ...extra,
})

const news = (id, extra) => ({
  id,
  title: `Test news ${id}`,
  content: 'First paragraph.\n\nSecond paragraph.',
  image_url: null,
  type: 'announcement',
  pinned: false,
  created_at: '2026-11-12T10:00:00Z',
  is_new: false,
  ...extra,
})

const DIGEST = {
  date: '2026-11-13',
  empty: false,
  me: { display_name: 'Alice', avatar_url: null, avatar_effect: 'community', tier: 'gold' },
  level: {
    level: 12,
    xp: 340,
    xp_current_level: 300,
    xp_next_level: 500,
    xp_into_level: 40,
    percent: 68,
    maxed: false,
    title_key: 'regular',
    tier: 'gold',
    xp_yesterday: 45,
  },
  expiry: { ends_at: '2026-12-12T12:00:00Z', days_left: 29 },
  news: [
    news(1, { pinned: true, is_new: true }),
    news(2, { type: 'maintenance', is_new: true }),
    news(3, { type: 'event' }),
  ],
  streak: 6,
  quota: { used: 6, max_allowed: 10, unlimited: false, remaining: 4 },
  tickets_open: 1,
  ranking: {
    position: 5,
    total: 12,
    movement: 2,
    top3: [
      entry(1, 'Bob', { trophies_won: 4, avatar_effect: 'ranking' }),
      entry(2, 'Carol', { movement: 1, trophies_won: 2 }),
      entry(3, 'Dave', { movement: -1 }),
      entry(5, 'Alice', { movement: 2, is_current_user: true, tier: 'gold' }),
    ],
  },
  next_achievement: {
    id: 'test',
    name_key: 'portal.dailyDigest.sections.nextAchievement',
    description_key: null,
    icon: 'moon',
    tier: 1,
    progress: 8,
    threshold: 10,
    remaining: 2,
  },
  recent_adds: Array.from({ length: 8 }, (_, n) => ({
    tmdb_id: 12345 + n,
    emby_item_id: `e${n}`,
    title: `Test Movie ${n + 1}`,
    year: '2024',
    media_type: n % 3 ? 'movie' : 'tv',
    poster_url: null,
    date_created: '2026-11-12',
  })),
  for_you: [
    {
      kind: 'request_available',
      title: 'Test Movie',
      at: hoursAgo(5),
      tmdb_id: 12345,
      media_type: 'movie',
      ticket_id: null,
    },
    {
      kind: 'request_approved',
      title: 'Test Show',
      at: hoursAgo(6),
      tmdb_id: 678,
      media_type: 'tv',
      ticket_id: null,
    },
    {
      kind: 'ticket_reply',
      title: 'Test Movie',
      at: hoursAgo(2),
      tmdb_id: null,
      media_type: null,
      ticket_id: 42,
    },
  ],
  events: [
    { id: 1, title: 'Test party', kind: 'public', scheduled_at: '2026-11-21T20:00:00Z' },
    { id: 2, title: 'Test marathon', kind: 'private', scheduled_at: '2026-11-28T19:30:00Z' },
  ],
}

async function openDigest(page, compact) {
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await page.addInitScript(() => window.localStorage.setItem('mediakeeper_locale', 'fr'))
  const tracker = await mockAuthenticatedPortal(page, {
    pageHandlers: portalListsHandlers(),
    extraOverrides: [
      {
        name: 'portal-daily-digest-open',
        match: url => url.pathname === '/api/portal/daily-digest',
        handler: jsonResponse({ dismissed: false, compact, digest: DIGEST }),
      },
    ],
  })
  await page.goto('/portal/lists')
  const dialog = page.getByRole('dialog', { name: "Quoi de neuf aujourd'hui ?" })
  await expect(dialog).toBeVisible()
  await expect(page.getByRole('switch', { name: 'Vue compacte' })).toHaveAttribute(
    'aria-checked',
    String(compact),
  )
  return tracker
}

async function expectNoViolation(page) {
  const results = await new AxeBuilder({ page }).include('.dd-panel').analyze()
  expect(results.violations, JSON.stringify(results.violations, null, 2)).toEqual([])
}

for (const compact of [false, true]) {
  test(`the daily digest passes axe in its ${compact ? 'compact' : 'full'} view`, async ({
    page,
  }) => {
    const tracker = await openDigest(page, compact)
    await expectNoViolation(page)
    expect(tracker.unexpected).toEqual([])
  })
}
