// Shared by the tests of the leaderboard page: the composable is stubbed, so each test
// drives the page with a fixture array of entries.
import { mount } from '@vue/test-utils'
import { ref } from 'vue'
import { vi } from 'vitest'

export function buildEntries(count, { offsetRank = 1 } = {}) {
  return Array.from({ length: count }, (_, i) => ({
    rank: offsetRank + i,
    user_id: 1000 + i,
    display_name: `User ${offsetRank + i}`,
    avatar_url: null,
    level: 10 + i,
    tier: 'gold',
    title_key: 'regular',
    period_xp: 1000 - i * 10,
    selected_title: null,
    title_tier: null,
    is_current_user: false,
    movement: 0,
  }))
}

export function buildStats(overrides = {}) {
  return {
    period_label: 'Mai 2026',
    total_players: 42,
    total_xp: 100000,
    days_remaining: 12,
    days_in_month: 31,
    my_xp: 500,
    my_delta_week: 100,
    projected_end_rank: 5,
    ...overrides,
  }
}

export const composableState = {
  entries: ref([]),
  stats: ref(null),
  viewerRank: ref(null),
  viewerEntry: ref(null),
  loading: ref(false),
  fetchTop: vi.fn(() => Promise.resolve(composableState.entries.value)),
}

const RouterLinkStub = {
  props: ['to'],
  template: '<a :data-to="JSON.stringify(to)"><slot /></a>',
}

export async function mountPage({
  entries,
  stats = null,
  viewerRank = null,
  viewerEntry = null,
  $t,
} = {}) {
  composableState.entries.value = entries
  composableState.stats.value = stats
  composableState.viewerRank.value = viewerRank
  composableState.viewerEntry.value = viewerEntry
  composableState.loading.value = false
  const PortalLeaderboard = (await import('@/views/portal/PortalLeaderboard.vue')).default
  return mount(PortalLeaderboard, {
    global: {
      mocks: $t ? { $t } : {},
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
