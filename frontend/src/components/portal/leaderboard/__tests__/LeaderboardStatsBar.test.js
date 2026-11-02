/**
 * Monthly stats bar — real translations, so the plural forms and the XP
 * label are checked as a player reads them.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createI18n } from 'vue-i18n'

import en from '@/locales/en.json'
import fr from '@/locales/fr.json'
import LeaderboardStatsBar from '../LeaderboardStatsBar.vue'

const realMatchMedia = window.matchMedia

async function barText(locale, stats) {
  const i18n = createI18n({ legacy: false, locale, messages: { fr, en } })
  const wrapper = mount(LeaderboardStatsBar, {
    props: {
      stats: {
        month_label: 'Mai 2026',
        total_players: 3,
        total_xp_month: 900,
        total_trophies_month: 7,
        days_remaining: 12,
        ...stats,
      },
    },
    global: { mocks: { $t: i18n.global.t } },
  })
  await flushPromises()
  return wrapper.text()
}

describe('LeaderboardStatsBar.vue', () => {
  beforeEach(() => {
    // Reduced motion makes the counters snap to their final value.
    window.matchMedia = vi.fn(() => ({ matches: true }))
  })

  afterEach(() => {
    window.matchMedia = realMatchMedia
  })

  it('names the XP total as activity XP, in French and in English', async () => {
    expect(await barText('fr')).toContain("900 XP d'activité")
    expect(await barText('en')).toContain('900 activity XP')
  })

  it('counts the trophies of the month, with the right plural form', async () => {
    expect(await barText('fr')).toContain('7 trophées distribués')
    expect(await barText('en')).toContain('7 trophies awarded')
    expect(await barText('fr', { total_trophies_month: 1 })).toContain('1 trophée distribué')
    expect(await barText('en', { total_trophies_month: 1 })).toContain('1 trophy awarded')
  })

  it('shows zero trophies when the payload has none', async () => {
    expect(await barText('en', { total_trophies_month: 0 })).toContain('0 trophies awarded')
  })
})
