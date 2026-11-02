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

async function mountBar(locale, stats) {
  const i18n = createI18n({ legacy: false, locale, messages: { fr, en } })
  const wrapper = mount(LeaderboardStatsBar, {
    props: {
      stats: {
        period_label: 'Mai 2026',
        total_players: 3,
        total_xp: 900,
        total_trophies: 7,
        days_remaining: 12,
        ...stats,
      },
    },
    global: { mocks: { $t: i18n.global.t } },
  })
  await flushPromises()
  return wrapper
}

async function barText(locale, stats) {
  return (await mountBar(locale, stats)).text()
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
    expect(await barText('fr', { total_trophies: 1 })).toContain('1 trophée distribué')
    expect(await barText('en', { total_trophies: 1 })).toContain('1 trophy awarded')
  })

  it('shows zero trophies when the payload has none', async () => {
    expect(await barText('en', { total_trophies: 0 })).toContain('0 trophies awarded')
  })

  it('agrees the ranked players with their number', async () => {
    expect(await barText('fr')).toContain('3 joueurs classés')
    expect(await barText('en')).toContain('3 ranked players')
    expect(await barText('fr', { total_players: 1 })).toContain('1 joueur classé')
    expect(await barText('en', { total_players: 1 })).toMatch(/1 ranked player(?!s)/)
    expect(await barText('fr', { total_players: 0 })).toContain('0 joueurs classés')
  })

  it('agrees the days left with their number, for the screen reader too', async () => {
    const dayLabels = {
      fr: { 12: '12 jours restants', 1: '1 jour restant', 0: '0 jours restants' },
      en: { 12: '12 days remaining', 1: '1 day remaining', 0: '0 days remaining' },
    }
    for (const [locale, labels] of Object.entries(dayLabels)) {
      for (const [days, label] of Object.entries(labels)) {
        const bar = await mountBar(locale, { days_remaining: Number(days) })
        expect(bar.text()).toContain(label)
        expect(bar.find('.lb-stats-progress').attributes('aria-label')).toBe(label)
      }
    }
  })
})
