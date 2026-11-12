/**
 * Monthly stats bar — real translations, so the plural forms and the XP
 * label are checked as a player reads them.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createI18n } from 'vue-i18n'

import { applyLocaleEphemeral, getLocale } from '@/i18n'
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
        days_in_month: 31,
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
    window.matchMedia = vi.fn(() => ({
      matches: true,
      addEventListener: () => {},
      removeEventListener: () => {},
    }))
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

  it('groups the digits as the app language does, whatever the browser speaks', async () => {
    const initial = getLocale()
    try {
      await applyLocaleEphemeral('fr')
      expect(await barText('fr', { total_xp: 12345 })).toContain("12 345 XP d'activité")
      await applyLocaleEphemeral('en')
      expect(await barText('en', { total_xp: 12345 })).toContain('12,345 activity XP')
    } finally {
      await applyLocaleEphemeral(initial)
    }
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

  it('leaves out the days left on a period that does not end with the month', async () => {
    const bar = await mountBar('fr', { days_remaining: null, period_label: 'Du 2 au 8 novembre' })
    expect(bar.text()).toContain('Du 2 au 8 novembre')
    expect(bar.text()).toContain('3 joueurs classés')
    expect(bar.text()).not.toContain('restant')
    expect(bar.find('.lb-stats-progress').exists()).toBe(false)
    expect(bar.findAll('.lb-stats-chip')).toHaveLength(4)
    expect(bar.findAll('.lb-stats-sep')).toHaveLength(3)
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

  describe('month ring', () => {
    const CIRCUMFERENCE = 2 * Math.PI * 10

    async function ringOffset(stats) {
      const bar = await mountBar('fr', stats)
      return Number(bar.find('.lb-stats-progress-fill').attributes('stroke-dashoffset'))
    }

    beforeEach(() => {
      // The last day of a month in this browser: the ring must not read it.
      vi.useFakeTimers({ toFake: ['Date'], now: new Date(2026, 9, 31, 19, 30) })
    })

    afterEach(() => {
      vi.useRealTimers()
    })

    it('follows the days the server counts, whatever the date of the browser', async () => {
      const firstDay = await ringOffset({ days_remaining: 29, days_in_month: 30 })
      expect(firstDay).toBeCloseTo(CIRCUMFERENCE * (1 - 1 / 30))
    })

    it('fills halfway through the month and entirely on its last day', async () => {
      expect(await ringOffset({ days_remaining: 15, days_in_month: 30 })).toBeCloseTo(
        CIRCUMFERENCE / 2,
      )
      expect(await ringOffset({ days_remaining: 0, days_in_month: 30 })).toBeCloseTo(0)
    })

    it('stays empty when the month length is missing', async () => {
      expect(await ringOffset({ days_in_month: null })).toBeCloseTo(CIRCUMFERENCE)
    })
  })
})
