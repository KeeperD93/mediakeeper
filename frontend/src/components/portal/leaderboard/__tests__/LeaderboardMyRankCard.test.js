/**
 * My-rank card — the three rendering paths (podium / top / hors-top).
 *
 *   1. ``inListEntry`` with rank ≤ 3 → "podium" message visible.
 *   2. ``inListEntry`` with rank 4..100 → stats row visible.
 *   3. ``viewerEntry`` only (out of top-N) → stats row visible with the
 *      absolute viewer rank.
 */
import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'

import LeaderboardMyRankCard from '@/components/portal/leaderboard/LeaderboardMyRankCard.vue'

vi.mock('vue-i18n', () => ({
  useI18n: () => ({ t: key => key }),
}))

function buildEntry(overrides = {}) {
  return {
    rank: 5,
    user_id: 99,
    display_name: 'Me',
    avatar_url: null,
    level: 12,
    tier: 'silver',
    title_key: 'regular',
    month_xp: 600,
    movement: 0,
    selected_title: null,
    title_tier: null,
    is_current_user: true,
    ...overrides,
  }
}

function buildStats(overrides = {}) {
  return {
    my_xp_month: 600,
    my_delta_week: 100,
    projected_end_rank: 5,
    ...overrides,
  }
}

function mountCard(props) {
  return mount(LeaderboardMyRankCard, {
    props,
    global: {
      stubs: {
        MkAvatar: { template: '<div class="mk-avatar-stub" />' },
      },
    },
  })
}

describe('LeaderboardMyRankCard.vue', () => {
  it('shows the on-podium message when the viewer is in top 3', () => {
    const wrapper = mountCard({
      inListEntry: buildEntry({ rank: 2 }),
      stats: buildStats(),
    })
    expect(wrapper.find('.lb-my-rank-podium-msg').exists()).toBe(true)
    expect(wrapper.text()).toContain('portal.leaderboard.myRank.onPodium')
    expect(wrapper.find('.lb-my-rank-stats').exists()).toBe(false)
    expect(wrapper.find('.lb-my-rank-rank').text()).toBe('#2')
  })

  it('shows stats row when the viewer is in the top window (rank 4..N)', () => {
    const wrapper = mountCard({
      inListEntry: buildEntry({ rank: 7 }),
      stats: buildStats({ projected_end_rank: 6 }),
    })
    expect(wrapper.find('.lb-my-rank-podium-msg').exists()).toBe(false)
    expect(wrapper.find('.lb-my-rank-stats').exists()).toBe(true)
    expect(wrapper.find('.lb-my-rank-rank').text()).toBe('#7')
    expect(wrapper.text()).toContain('portal.leaderboard.myRank.xpThisMonth')
    expect(wrapper.text()).toContain('portal.leaderboard.myRank.projectedEnd')
  })

  it('renders the absolute rank when the viewer is outside the top window', () => {
    const wrapper = mountCard({
      viewerRank: 42,
      viewerEntry: buildEntry({ rank: 42, display_name: 'Me42' }),
      stats: buildStats({ projected_end_rank: 38 }),
    })
    expect(wrapper.find('.lb-my-rank-rank').text()).toBe('#42')
    expect(wrapper.find('.lb-my-rank-stats').exists()).toBe(true)
    expect(wrapper.text()).toContain('Me42')
  })
})
