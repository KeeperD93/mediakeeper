/**
 * Level and title of a player — written the same way on every row of the
 * ranking, in the language of the reader.
 */
import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'

import LeaderboardCard from '@/components/portal/profile/LeaderboardCard.vue'
import en from '@/locales/en.json'
import fr from '@/locales/fr.json'
import LeaderboardLevelTitle from '../LeaderboardLevelTitle.vue'
import LeaderboardTopTenRow from '../LeaderboardTopTenRow.vue'

vi.mock('vue-i18n', () => ({
  useI18n: () => ({ t: key => key }),
}))

function buildEntry() {
  return {
    rank: 4,
    user_id: 7,
    display_name: 'Alice',
    avatar_url: null,
    level: 12,
    tier: 'gold',
    title_key: 'regular',
    month_xp: 100,
    selected_title: 'portal.titles.supremeCollector',
    title_tier: 6,
    is_current_user: false,
    movement: 0,
  }
}

const SURFACES = {
  topTen: entry => mount(LeaderboardTopTenRow, { props: { entry } }).find('.lb-top-row-title'),
  profileCard: entry => mount(LeaderboardCard, { props: { entries: [entry] } }).find('.gc-lb-tier'),
}

describe('LeaderboardLevelTitle.vue', () => {
  it.each([
    ['fr', 'Niveau 12 · Habitué'],
    ['en', 'Level 12 · Regular'],
  ])('reads the level and the title in %s', async (locale, expected) => {
    const { createI18n } = await vi.importActual('vue-i18n')
    const { t } = createI18n({ legacy: false, locale, messages: { fr, en } }).global
    const entry = { ...buildEntry(), selected_title: null }
    const wrapper = mount(LeaderboardLevelTitle, {
      props: { entry },
      global: { mocks: { $t: t } },
    })
    expect(wrapper.text()).toBe(expected)
  })

  it('falls back on the first title without a known one', () => {
    const entry = { ...buildEntry(), title_key: null }
    const wrapper = mount(LeaderboardLevelTitle, { props: { entry } })
    expect(wrapper.text()).toContain('portal.profile.titles.spectator')
  })

  it.each(Object.keys(SURFACES))('shows the level before the chosen title on %s', surface => {
    const text = SURFACES[surface](buildEntry()).text()
    expect(text).toContain('"level":12')
    expect(text.indexOf('"level":12')).toBeLessThan(text.indexOf('portal.titles.supremeCollector'))
  })
})
