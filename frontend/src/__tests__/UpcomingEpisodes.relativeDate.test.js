/**
 * Covers the `relativeDate` branch logic in UpcomingEpisodes.vue —
 * verifies that each day-diff bucket produces the expected i18n key
 * call (today / tomorrow / days / weeks / months / past).
 *
 * `relativeDate` is inlined in the SFC <script setup> rather than
 * exported, so the test mounts the component with fake timers + a
 * mocked apiGet that returns episodes with controlled `air_date`
 * strings, then asserts the rendered `.uc-badge` text content. The
 * i18n stub returns `key:JSON(params)` so plural keys remain
 * distinguishable from singular keys.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

const apiGet = vi.fn()

vi.mock('@/composables/useApi', () => ({
  useApi: () => ({
    apiGet,
    apiPost: vi.fn(),
    apiPut: vi.fn(),
    apiDelete: vi.fn(),
    apiPatch: vi.fn(),
    apiFetch: vi.fn(),
    loading: { value: false },
    error: { value: null },
  }),
}))

vi.mock('vue-i18n', async () => {
  const { ref } = await vi.importActual('vue')
  return {
    useI18n: () => ({
      t: (key, params) => {
        if (params && typeof params === 'object') return `${key}:${JSON.stringify(params)}`
        return key
      },
      locale: ref('fr'),
    }),
  }
})

import UpcomingEpisodes from '@/components/dashboard/UpcomingEpisodes.vue'

const FIXED_NOW = new Date('2026-06-15T12:00:00Z').getTime()

function isoOffset(days) {
  const d = new Date(FIXED_NOW)
  d.setUTCDate(d.getUTCDate() + days)
  return d.toISOString().slice(0, 10)
}

function buildEpisode(days) {
  return {
    series_name: `S${days}`,
    season: 1,
    episode: 1,
    air_date: isoOffset(days),
    tmdb_id: 1,
    poster: null,
  }
}

describe('UpcomingEpisodes — relativeDate buckets', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(FIXED_NOW)
    apiGet.mockReset()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it.each([
    [-3, '-dashboard.upcomingInDays:{"n":3}'],
    [-1, '-dashboard.upcomingInDays:{"n":1}'],
    [0, 'common.today'],
    [1, 'common.tomorrow'],
    [6, 'dashboard.upcomingInDays:{"n":6}'],
    [7, 'dashboard.upcomingInWeeks:{"n":1}'],
    [13, 'dashboard.upcomingInWeeks:{"n":2}'],
    [30, 'dashboard.upcomingInMonths:{"n":1}'],
    [60, 'dashboard.upcomingInMonths:{"n":2}'],
  ])('renders bucket label for diff=%i days', async (days, expected) => {
    apiGet.mockResolvedValueOnce([buildEpisode(days)])

    const w = mount(UpcomingEpisodes)
    await flushPromises()

    const badges = w.findAll('.uc-badge')
    expect(badges.length).toBeGreaterThan(0)
    // The carousel duplicates episodes for the looped scroll, so we
    // assert the first badge — both copies render identical text.
    expect(badges[0].text()).toContain(expected)

    w.unmount()
  })

  it('returns empty string for missing air_date (no badge crash)', async () => {
    apiGet.mockResolvedValueOnce([
      {
        series_name: 'Empty',
        season: 1,
        episode: 1,
        air_date: '',
        tmdb_id: 2,
        poster: null,
      },
    ])

    const w = mount(UpcomingEpisodes)
    await flushPromises()

    const badge = w.find('.uc-badge')
    expect(badge.exists()).toBe(true)
    // Empty string rendering produces only the dot + whitespace.
    expect(badge.text().trim()).toBe('')

    w.unmount()
  })
})
