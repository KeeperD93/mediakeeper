/**
 * Premium leaderboard page — rendering coverage.
 *
 * Stubs the composable so we drive the page deterministically with a
 * fixture array of entries. The page must:
 *   - render the hero billboard for rank #1, the two-card podium
 *     (ranks #2 + #3), the my-rank card, the top-10 block (ranks 4-13)
 *     and the rest table (ranks 14+).
 *   - surface the emptyState message when the API returns nothing.
 *   - NOT mount the legacy ``AchievementBadge`` grid (regression
 *     guard — that block belonged to the old design).
 *   - point each rest row at /portal/u/:id.
 */
import { describe, it, expect, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'

vi.mock('vue-i18n', () => ({
  useI18n: () => ({ t: key => key }),
}))

function buildEntries(count, { offsetRank = 1 } = {}) {
  return Array.from({ length: count }, (_, i) => ({
    rank: offsetRank + i,
    user_id: 1000 + i,
    display_name: `User ${offsetRank + i}`,
    avatar_url: null,
    level: 10 + i,
    tier: 'gold',
    title_key: 'regular',
    month_xp: 1000 - i * 10,
    selected_title: null,
    title_tier: null,
    is_current_user: false,
    movement: 0,
  }))
}

function buildStats(overrides = {}) {
  return {
    month_label: 'Mai 2026',
    total_players: 42,
    total_xp_month: 100000,
    days_remaining: 12,
    my_xp_month: 500,
    my_delta_week: 100,
    projected_end_rank: 5,
    ...overrides,
  }
}

const composableState = {
  entries: ref([]),
  stats: ref(null),
  viewerRank: ref(null),
  viewerEntry: ref(null),
  loading: ref(false),
  fetchTop: vi.fn(() => Promise.resolve(composableState.entries.value)),
}

vi.mock('@/composables/portal/useMonthlyLeaderboard', () => ({
  useMonthlyLeaderboard: () => composableState,
}))

const RouterLinkStub = {
  props: ['to'],
  template: '<a :data-to="JSON.stringify(to)"><slot /></a>',
}

async function mountPage({ entries, stats = null, viewerRank = null, viewerEntry = null } = {}) {
  composableState.entries.value = entries
  composableState.stats.value = stats
  composableState.viewerRank.value = viewerRank
  composableState.viewerEntry.value = viewerEntry
  composableState.loading.value = false
  const PortalLeaderboard = (await import('@/views/portal/PortalLeaderboard.vue')).default
  return mount(PortalLeaderboard, {
    global: {
      stubs: {
        'router-link': RouterLinkStub,
        MkAvatar: { template: '<div class="mk-avatar-stub" />' },
        LeaderboardHeroBillboard: { template: '<div class="lb-hero-stub" />' },
        LeaderboardStatsBar: { template: '<div class="lb-stats-stub" />' },
        LeaderboardMyRankCard: { template: '<div class="lb-my-rank-stub" />' },
        LeaderboardTopTenRow: { template: '<div class="lb-top-row-stub" />' },
        PortalLeaderboardPodium: {
          props: ['entries'],
          template: '<div class="pt-lb-podium-stub" :data-count="entries.length" />',
        },
      },
    },
  })
}

describe('PortalLeaderboard.vue', () => {
  it('renders hero + 2-card podium + my-rank + top-10 + rest sections for a full payload', async () => {
    const wrapper = await mountPage({
      entries: buildEntries(20),
      stats: buildStats(),
    })
    await flushPromises()
    expect(wrapper.find('.lb-hero-stub').exists()).toBe(true)
    expect(wrapper.find('.lb-stats-stub').exists()).toBe(true)
    const podium = wrapper.find('.pt-lb-podium-stub')
    expect(podium.exists()).toBe(true)
    expect(podium.attributes('data-count')).toBe('2')
    expect(wrapper.findAll('.lb-top-row-stub')).toHaveLength(10)
    // Rest rows = ranks 14..20 → 7 entries.
    expect(wrapper.findAll('.gc-lb-row')).toHaveLength(7)
  })

  it('keeps the 100-entry payload split: hero + 2 podium + 10 top + 87 rest rows', async () => {
    const wrapper = await mountPage({ entries: buildEntries(100), stats: buildStats() })
    await flushPromises()
    expect(wrapper.find('.lb-hero-stub').exists()).toBe(true)
    expect(wrapper.find('.pt-lb-podium-stub').attributes('data-count')).toBe('2')
    expect(wrapper.findAll('.lb-top-row-stub')).toHaveLength(10)
    expect(wrapper.findAll('.gc-lb-row')).toHaveLength(87)
  })

  it('renders the empty-state message when the API returns nothing', async () => {
    const wrapper = await mountPage({ entries: [] })
    await flushPromises()
    expect(wrapper.text()).toContain('portal.leaderboard.emptyState')
    expect(wrapper.find('.lb-hero-stub').exists()).toBe(false)
    expect(wrapper.find('.pt-lb-podium-stub').exists()).toBe(false)
    expect(wrapper.find('.gc-lb-row').exists()).toBe(false)
  })

  it('renders the my-rank card when the viewer is outside the top via viewerEntry', async () => {
    const viewerEntry = {
      rank: 42,
      user_id: 999,
      display_name: 'Me',
      avatar_url: null,
      level: 3,
      tier: 'bronze',
      title_key: 'spectator',
      month_xp: 80,
      selected_title: null,
      title_tier: null,
      is_current_user: true,
      movement: 0,
    }
    const wrapper = await mountPage({
      entries: buildEntries(20),
      stats: buildStats(),
      viewerRank: 42,
      viewerEntry,
    })
    await flushPromises()
    expect(wrapper.find('.lb-my-rank-stub').exists()).toBe(true)
  })

  it('never mounts the legacy AchievementBadge grid (regression guard)', async () => {
    const wrapper = await mountPage({ entries: buildEntries(8), stats: buildStats() })
    await flushPromises()
    expect(wrapper.find('.achievement-badge').exists()).toBe(false)
    expect(wrapper.html()).not.toContain('AchievementBadge')
    expect(wrapper.html()).not.toContain('myProgress')
  })

  it('points each rest row at /portal/u/:id', async () => {
    const wrapper = await mountPage({ entries: buildEntries(15), stats: buildStats() })
    await flushPromises()
    const rows = wrapper.findAll('.gc-lb-row')
    expect(rows.length).toBe(2)
    // First rest row is rank 14 — user_id 1013 with the buildEntries offset.
    expect(rows[0].attributes('data-to')).toContain('"id":1013')
  })
})
