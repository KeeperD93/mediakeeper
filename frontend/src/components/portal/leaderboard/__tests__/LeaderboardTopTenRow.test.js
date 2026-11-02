/**
 * Top ten rows — the level colors the avatar ring, never the position.
 */
import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'

import MkAvatar from '@/components/common/MkAvatar.vue'
import LeaderboardTopTenRow from '../LeaderboardTopTenRow.vue'

vi.mock('vue-i18n', () => ({
  useI18n: () => ({ t: key => key }),
}))

function buildEntry(tier) {
  return {
    rank: 4,
    user_id: 7,
    display_name: 'Alice',
    avatar_url: null,
    level: 10,
    tier,
    title_key: 'regular',
    month_xp: 100,
    selected_title: null,
    title_tier: null,
    is_current_user: false,
    movement: 0,
  }
}

describe('LeaderboardTopTenRow.vue', () => {
  it.each(['bronze', 'gold', 'platinum', 'diamond', 'master', 'legendary'])(
    'keeps a neutral position and colors only the avatar for a %s player',
    tier => {
      const wrapper = mount(LeaderboardTopTenRow, { props: { entry: buildEntry(tier) } })
      const position = wrapper.find('.lb-top-row-rank')
      expect(position.classes()).toEqual(['lb-top-row-rank'])
      expect(position.text()).toBe('4')
      expect(wrapper.findComponent(MkAvatar).props('tier')).toBe(tier)
    },
  )
})
