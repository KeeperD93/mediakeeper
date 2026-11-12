/**
 * "You" label — every place a viewer can appear in the ranking marks them, and
 * nobody else, in the language of the reader.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'

import en from '@/locales/en.json'
import fr from '@/locales/fr.json'
import LeaderboardHeroBillboard from '../LeaderboardHeroBillboard.vue'
import LeaderboardMePill from '../LeaderboardMePill.vue'
import LeaderboardTopTenRow from '../LeaderboardTopTenRow.vue'
import PortalLeaderboardPodium from '../PortalLeaderboardPodium.vue'

vi.mock('vue-i18n', async importOriginal => ({
  ...(await importOriginal()),
  useI18n: () => ({ t: key => key }),
}))

function buildEntry(isCurrentUser) {
  return {
    rank: 2,
    user_id: 7,
    display_name: 'Alice',
    avatar_url: null,
    level: 10,
    tier: 'gold',
    title_key: 'regular',
    period_xp: 100,
    selected_title: null,
    title_tier: null,
    is_current_user: isCurrentUser,
    movement: 0,
  }
}

const SURFACES = {
  hero: entry => mount(LeaderboardHeroBillboard, { props: { entry } }),
  podium: entry => mount(PortalLeaderboardPodium, { props: { entries: [entry] } }),
  topTen: entry => mount(LeaderboardTopTenRow, { props: { entry } }),
}

describe('LeaderboardMePill.vue', () => {
  beforeEach(() => {
    vi.stubGlobal(
      'matchMedia',
      vi.fn(() => ({
        matches: false,
        addEventListener: () => {},
        removeEventListener: () => {},
      })),
    )
  })
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it.each(Object.keys(SURFACES))('marks the viewer on %s', surface => {
    expect(SURFACES[surface](buildEntry(true)).find('.lb-me-pill').exists()).toBe(true)
  })

  it.each(Object.keys(SURFACES))('marks nobody else on %s', surface => {
    expect(SURFACES[surface](buildEntry(false)).find('.lb-me-pill').exists()).toBe(false)
  })

  it.each([
    ['fr', 'VOUS'],
    ['en', 'YOU'],
  ])('reads the label in %s', async (locale, label) => {
    const { createI18n } = await vi.importActual('vue-i18n')
    const { t } = createI18n({ legacy: false, locale, messages: { fr, en } }).global
    const wrapper = mount(LeaderboardMePill, { global: { mocks: { $t: t } } })
    expect(wrapper.text()).toBe(label)
  })
})
