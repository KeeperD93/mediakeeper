/**
 * Chosen title — every leaderboard surface shows it the same way, in the
 * color of its rarity, and a player without one sees no difference.
 */
import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'

import LeaderboardCard from '@/components/portal/profile/LeaderboardCard.vue'
import LeaderboardChosenTitle from '../LeaderboardChosenTitle.vue'
import LeaderboardTopTenRow from '../LeaderboardTopTenRow.vue'
import PortalLeaderboardPodium from '../PortalLeaderboardPodium.vue'

vi.mock('vue-i18n', () => ({
  useI18n: () => ({ t: key => key }),
}))

const TITLE = 'portal.titles.testTitle'

function buildEntry(overrides = {}) {
  return {
    rank: 4,
    user_id: 7,
    display_name: 'Alice',
    avatar_url: null,
    level: 10,
    tier: 'gold',
    title_key: 'regular',
    month_xp: 100,
    selected_title: TITLE,
    title_tier: 4,
    is_current_user: false,
    movement: 0,
    ...overrides,
  }
}

const SURFACES = {
  podium: entry => mount(PortalLeaderboardPodium, { props: { entries: [entry] } }),
  topTen: entry => mount(LeaderboardTopTenRow, { props: { entry } }),
  profileCard: entry => mount(LeaderboardCard, { props: { entries: [entry] } }),
}

describe('LeaderboardChosenTitle.vue', () => {
  it('shows the title in the color of its rarity', () => {
    const wrapper = mount(LeaderboardChosenTitle, { props: { entry: buildEntry() } })
    expect(wrapper.text()).toBe(`· ${TITLE}`)
    expect(wrapper.classes()).toContain('gc-lb-custom-title--rarity-epic')
  })

  it('reads each rarity, and an unknown one as common', () => {
    const rarities = {
      1: 'common',
      2: 'uncommon',
      3: 'rare',
      4: 'epic',
      5: 'legendary',
      6: 'mythic',
      99: 'common',
    }
    for (const [tier, rarity] of Object.entries(rarities)) {
      const entry = buildEntry({ title_tier: Number(tier) })
      const wrapper = mount(LeaderboardChosenTitle, { props: { entry } })
      expect(wrapper.classes()).toContain(`gc-lb-custom-title--rarity-${rarity}`)
    }
  })

  it('keeps the base color for a title without rarity', () => {
    const entry = buildEntry({ title_tier: null })
    const wrapper = mount(LeaderboardChosenTitle, { props: { entry } })
    expect(wrapper.classes()).toEqual(['gc-lb-custom-title'])
  })

  it('shows nothing without a chosen title', () => {
    const entry = buildEntry({ selected_title: null })
    const wrapper = mount(LeaderboardChosenTitle, { props: { entry } })
    expect(wrapper.find('em').exists()).toBe(false)
  })

  it.each(Object.keys(SURFACES))('appears next to the level title on %s', surface => {
    const title = SURFACES[surface](buildEntry()).find('.gc-lb-custom-title')
    expect(title.text()).toBe(`· ${TITLE}`)
    expect(title.element.parentElement.textContent).toContain('portal.profile.titles.regular')
  })

  it.each(Object.keys(SURFACES))('stays away from %s without a chosen title', surface => {
    const wrapper = SURFACES[surface](buildEntry({ selected_title: null }))
    expect(wrapper.find('.gc-lb-custom-title').exists()).toBe(false)
    expect(wrapper.text()).toContain('portal.profile.titles.regular')
  })
})
