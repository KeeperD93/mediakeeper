// Authenticated Portal mock layer — composes on top of api-mocks.js.
//
// Goal: drive Portal-only Playwright smoke tests without booting a real
// backend, a real session, or a real account. Every handler in this file
// returns a deterministic, fully-fictional payload so the page renders
// the "logged-in viewer with nothing to show" baseline (empty lists,
// empty news, empty tickets, etc.).
//
// No secrets, no real users, no third-party hosts.

import { mockApi, jsonResponse } from './api-mocks.js'

// Fictional viewer used by every authenticated smoke test. Override
// individual fields via ``mockAuthenticatedPortal({ profile: { ... } })``
// when a test needs a different role/locale/feature flag.
export const DEFAULT_VIEWER_PROFILE = Object.freeze({
  id: 101,
  user_id: 101,
  username: 'e2e.viewer',
  display_name: 'E2E Viewer',
  role: 'user',
  language: 'en',
  chat_enabled: false,
  has_backoffice_access: false,
  display_name_must_set: false,
  hide_adult: true,
  is_public: true,
  bio: '',
  avatar_url: null,
  avatar_custom_path: null,
  avatar_is_custom: false,
  selected_title: null,
  avatar_effect: null,
  selected_badges: [],
  favorite_genres: [],
})

const DEFAULT_GDPR = Object.freeze({
  enabled: false,
  deletion_requested_at: null,
  pending_deletion_at: null,
})

const DEFAULT_UI = Object.freeze({ show_requests_tab: false })

function pathHandler(name, pathname, body, status = 200) {
  return {
    name,
    match: url => url.pathname === pathname,
    handler: jsonResponse(body, status),
  }
}

/**
 * Handlers covering every /api/portal call PortalLayout fires at boot:
 * /auth/me, /news/unread, /changelog/check, /daily-digest, /events/rooms,
 * /notifications/count.
 *
 * The chat websocket is NOT mocked — ``chat_enabled: false`` short-circuits
 * ``initGlobalChat`` before any /api/portal/chat call is made.
 */
export function portalLayoutHandlers({
  profile = DEFAULT_VIEWER_PROFILE,
  unreadNewsCount = 0,
  ui = DEFAULT_UI,
  gdpr = DEFAULT_GDPR,
} = {}) {
  return [
    pathHandler('portal-auth-me-authenticated', '/api/portal/auth/me', {
      profile: { ...profile },
      unread_news_count: unreadNewsCount,
      ui: { ...ui },
      gdpr: { ...gdpr },
    }),
    pathHandler('portal-news-unread', '/api/portal/news/unread', { items: [] }),
    pathHandler('portal-changelog-check', '/api/portal/changelog/check', {
      has_new: false,
      current_version: '0.0.0-e2e',
    }),
    pathHandler('portal-daily-digest', '/api/portal/daily-digest', {
      dismissed: true,
      digest: null,
    }),
    pathHandler('portal-events-rooms', '/api/portal/events/rooms', { items: [] }),
    pathHandler('portal-maintenance', '/api/portal/maintenance', { enabled: false, text: '' }),
    pathHandler('portal-notifications-count', '/api/portal/notifications/count', { unread: 0 }),
  ]
}

/** Handlers for /portal/lists (both "Mine" and "Public" tabs). */
export function portalListsHandlers() {
  return [
    pathHandler('portal-lists-mine', '/api/portal/lists', { items: [] }),
    pathHandler('portal-lists-public', '/api/portal/lists/public', { items: [] }),
  ]
}

/** Handlers for /portal/settings (every tab — appearance, identity, ...). */
export function portalSettingsHandlers({ profile = DEFAULT_VIEWER_PROFILE } = {}) {
  return [
    pathHandler('portal-username-state', '/api/portal/profiles/me/username-state', {
      must_set: false,
      locked: false,
      locked_until: null,
      lock_days: 180,
      current: profile.display_name || profile.username || '',
    }),
    pathHandler('portal-titles', '/api/portal/profiles/me/titles', {
      titles: [],
      catalogue: [],
    }),
    pathHandler('portal-avatar-effects', '/api/portal/profiles/me/avatar-effects', {
      effects: [],
    }),
    // Profile core + lists wave — empty payloads keep the hero in its
    // "no data yet" state without spawning availability batch calls.
    pathHandler('portal-catalog-profile-full', '/api/portal/catalog/profile-full', null),
    pathHandler('portal-achievements-me', '/api/portal/achievements/me', null),
    pathHandler(
      'portal-catalog-recommendations-full',
      '/api/portal/catalog/recommendations-full',
      null,
    ),
    pathHandler('portal-library-continue', '/api/portal/library/continue', null),
    pathHandler(
      'portal-catalog-recommended-for-me',
      '/api/portal/catalog/recommended-for-me',
      null,
    ),
    // Same pathname for both ?media_type=tv and ?media_type=movie.
    pathHandler(
      'portal-catalog-because-you-watched',
      '/api/portal/catalog/because-you-watched',
      null,
    ),
    pathHandler('portal-catalog-preferences-based', '/api/portal/catalog/preferences-based', null),
  ]
}

/** Handlers for /portal/tickets. */
export function portalTicketsHandlers() {
  return [
    pathHandler('portal-tickets', '/api/portal/tickets', {
      items: [],
      next_cursor: null,
      has_more: false,
    }),
  ]
}

/** Handlers for the dedicated /portal/leaderboard page. */
export function portalLeaderboardHandlers() {
  return [
    pathHandler(
      'portal-leaderboard-monthly',
      '/api/portal/achievements/leaderboard/monthly',
      {
        items: [],
        viewer_rank: null,
        viewer_entry: null,
        stats: {
          month_label: '',
          total_players: 0,
          total_xp_month: 0,
          days_remaining: 0,
          my_xp_month: null,
          my_delta_week: null,
          projected_end_rank: null,
        },
      },
    ),
  ]
}

/**
 * Install the authenticated-Portal mock layer on a Playwright page.
 *
 * @param {import('@playwright/test').Page} page
 * @param {object} [options]
 * @param {object} [options.profile] — override individual viewer fields.
 * @param {number} [options.unreadNewsCount]
 * @param {object} [options.ui]
 * @param {object} [options.gdpr]
 * @param {Array} [options.pageHandlers] — page-specific handlers
 *   (call ``portalListsHandlers()``, ``portalSettingsHandlers()``,
 *   ``portalTicketsHandlers()`` and spread the results here).
 * @param {Array} [options.extraOverrides] — free-form route overrides
 *   evaluated before everything else.
 * @returns {Promise<{unexpected: Array<{method: string, url: string}>}>}
 */
export async function mockAuthenticatedPortal(page, options = {}) {
  const {
    profile = DEFAULT_VIEWER_PROFILE,
    unreadNewsCount = 0,
    ui = DEFAULT_UI,
    gdpr = DEFAULT_GDPR,
    pageHandlers = [],
    extraOverrides = [],
  } = options

  const overrides = [
    ...extraOverrides,
    ...pageHandlers,
    ...portalLayoutHandlers({ profile, unreadNewsCount, ui, gdpr }),
  ]
  return mockApi(page, { overrides })
}
