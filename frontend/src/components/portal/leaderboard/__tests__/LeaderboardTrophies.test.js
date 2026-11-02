/**
 * Trophies won — every row of the ranking shows them, a player without any shows
 * nothing, and the first place keeps its lead without a trophy of its own.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'

import en from '@/locales/en.json'
import fr from '@/locales/fr.json'
import LeaderboardCard from '@/components/portal/profile/LeaderboardCard.vue'
import LeaderboardHeroBillboard from '../LeaderboardHeroBillboard.vue'
import LeaderboardMyRankCard from '../LeaderboardMyRankCard.vue'
import LeaderboardTopTenRow from '../LeaderboardTopTenRow.vue'
import LeaderboardTrophies from '../LeaderboardTrophies.vue'
import PortalLeaderboardPodium from '../PortalLeaderboardPodium.vue'

vi.mock('vue-i18n', () => ({
  useI18n: () => ({ t: key => key }),
}))

function buildEntry(trophies) {
  return {
    rank: 2,
    user_id: 7,
    display_name: 'Alice',
    avatar_url: null,
    level: 10,
    tier: 'gold',
    title_key: 'regular',
    month_xp: 100,
    selected_title: null,
    title_tier: null,
    is_current_user: false,
    movement: 0,
    trophies_won: trophies,
    lead_over_2: 14,
  }
}

const SURFACES = {
  hero: entry => mount(LeaderboardHeroBillboard, { props: { entry } }),
  podium: entry => mount(PortalLeaderboardPodium, { props: { entries: [entry] } }),
  topTen: entry => mount(LeaderboardTopTenRow, { props: { entry } }),
  card: entry => mount(LeaderboardCard, { props: { entries: [entry] } }),
  myRank: entry =>
    mount(LeaderboardMyRankCard, { props: { viewerRank: 120, viewerEntry: entry, stats: null } }),
}

async function readWith(locale, count) {
  const { createI18n } = await vi.importActual('vue-i18n')
  const { t } = createI18n({ legacy: false, locale, messages: { fr, en } }).global
  return mount(LeaderboardTrophies, { props: { count }, global: { mocks: { $t: t } } })
}

describe('LeaderboardTrophies.vue', () => {
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

  it.each(Object.keys(SURFACES))('shows the trophies won on %s', surface => {
    const trophies = SURFACES[surface](buildEntry(3)).find('.lb-trophies')
    expect(trophies.text()).toBe('+3')
    expect(trophies.find('svg').exists()).toBe(true)
  })

  it.each(Object.keys(SURFACES))('shows nothing for no trophy on %s', surface => {
    expect(SURFACES[surface](buildEntry(0)).find('.lb-trophies').exists()).toBe(false)
  })

  it.each(Object.keys(SURFACES))('shows nothing when the count is missing on %s', surface => {
    expect(SURFACES[surface](buildEntry(undefined)).find('.lb-trophies').exists()).toBe(false)
  })

  it('leaves the trophy icon to the trophies on the first place', () => {
    const wrapper = SURFACES.hero(buildEntry(3))
    expect(wrapper.find('.lb-hero-lead').exists()).toBe(true)
    expect(wrapper.find('.lb-hero-lead svg').exists()).toBe(false)
    expect(wrapper.find('.lb-hero-lead .lb-trophies').exists()).toBe(false)
  })

  it('hides the row of chips of a first place with no lead and no trophy', () => {
    const wrapper = SURFACES.hero({ ...buildEntry(0), lead_over_2: 0 })
    expect(wrapper.find('.lb-hero-chips').exists()).toBe(false)
  })

  it.each([
    ['fr', 1, '1 trophée gagné sur cette période'],
    ['fr', 3, '3 trophées gagnés sur cette période'],
    ['en', 1, '1 trophy won in this period'],
    ['en', 3, '3 trophies won in this period'],
  ])('names the trophies for a screen reader in %s (%i)', async (locale, count, label) => {
    const wrapper = await readWith(locale, count)
    expect(wrapper.attributes('aria-label')).toBe(label)
    expect(wrapper.attributes('title')).toBe(label)
    expect(wrapper.attributes('role')).toBe('img')
  })
})
