/**
 * My-rank card — for a viewer outside the list only: their row shows them
 * otherwise. Stats row visible with the absolute viewer rank.
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
    period_xp: 600,
    movement: 0,
    selected_title: null,
    title_tier: null,
    is_current_user: true,
    ...overrides,
  }
}

function buildStats(overrides = {}) {
  return {
    my_xp: 600,
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
  it('renders the absolute rank and the stats of a viewer outside the list', () => {
    const wrapper = mountCard({
      viewerRank: 142,
      viewerEntry: buildEntry({ rank: 142, display_name: 'Me142' }),
      stats: buildStats({ projected_end_rank: 138 }),
    })
    expect(wrapper.find('.lb-my-rank-rank').text()).toBe('#142')
    expect(wrapper.find('.lb-my-rank-stats').exists()).toBe(true)
    expect(wrapper.text()).toContain('Me142')
    expect(wrapper.text()).toContain('portal.leaderboard.myRank.xpThisMonth')
    expect(wrapper.text()).toContain('portal.leaderboard.myRank.projectedEnd')
  })

  it('shows nothing without a viewer outside the list', () => {
    const wrapper = mountCard({ viewerRank: null, viewerEntry: null, stats: buildStats() })
    expect(wrapper.find('.lb-my-rank').exists()).toBe(false)
  })
})
