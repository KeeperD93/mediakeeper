/**
 * Figures of the day: the streak and the open tickets show at 0 too, worded in the
 * singular in French (« 0 ticket ouvert »), while rank and quota show only when they apply.
 */
import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import { defineComponent, ref } from 'vue'
import { createI18n } from 'vue-i18n'

import en from '@/locales/en.json'
import fr from '@/locales/fr.json'
import { useDailyDigestPresenters } from '../useDailyDigestPresenters'

const digest = (extra = {}) => ({
  date: '2026-11-13',
  empty: false,
  ranking: { position: 0, total: 0, movement: 0, top3: [] },
  quota: { used: 0, max_allowed: 0, unlimited: true, remaining: -1 },
  tickets_open: 0,
  streak: 0,
  ...extra,
})

const cardsFor = (data, locale = 'fr') => {
  let cards
  const Probe = defineComponent({
    setup() {
      cards = useDailyDigestPresenters(ref(data)).statCards
      return () => null
    },
  })
  const i18n = createI18n({ legacy: false, locale, messages: { fr, en } })
  const wrapper = mount(Probe, { global: { plugins: [i18n] } })
  const out = Object.fromEntries(cards.value.map(card => [card.key, card]))
  wrapper.unmount()
  return out
}

describe('useDailyDigestPresenters — figures of the day', () => {
  it('shows the streak and the open tickets at 0, without rank or quota', () => {
    const cards = cardsFor(digest())
    expect(Object.keys(cards)).toEqual(['streak', 'tickets'])
    expect(cards.streak.value).toBe(0)
    expect(cards.tickets.value).toBe(0)
  })

  it('words 0 in the singular in French', () => {
    const { streak, tickets } = cardsFor(digest())
    expect(streak.caption).toBe('jour consécutif')
    expect(streak.compactCaption).toBe("Jour d'affilée")
    expect(tickets.caption).toBe('aucun à suivre')
    expect(tickets.compactCaption).toBe('Ticket ouvert')
  })

  it('words 0 in the plural in English', () => {
    const { streak, tickets } = cardsFor(digest(), 'en')
    expect(streak.caption).toBe('days in a row')
    expect(streak.compactCaption).toBe('Days in a row')
    expect(tickets.caption).toBe('none to follow up')
    expect(tickets.compactCaption).toBe('Open tickets')
  })

  it('keeps the singular at 1, the plural from 2, and the follow-up once a ticket is open', () => {
    const one = cardsFor(digest({ streak: 1, tickets_open: 1 }))
    expect(one.streak.caption).toBe('jour consécutif')
    expect(one.tickets.compactCaption).toBe('Ticket ouvert')
    expect(one.tickets.caption).toBe('à suivre')

    const two = cardsFor(digest({ streak: 2, tickets_open: 2 }))
    expect(two.streak.caption).toBe('jours consécutifs')
    expect(two.tickets.compactCaption).toBe('Tickets ouverts')

    const en = cardsFor(digest({ streak: 1, tickets_open: 1 }), 'en')
    expect(en.streak.caption).toBe('day in a row')
    expect(en.tickets.compactCaption).toBe('Open ticket')
  })

  it('adds rank and quota when they apply, in their order', () => {
    const cards = cardsFor(
      digest({
        ranking: { position: 5, total: 12, movement: 2, top3: [] },
        quota: { used: 6, max_allowed: 10, unlimited: false, remaining: 4 },
      }),
    )
    expect(Object.keys(cards)).toEqual(['rank', 'streak', 'quota', 'tickets'])
  })

  it('shows no card on an empty digest', () => {
    expect(cardsFor(digest({ empty: true }))).toEqual({})
  })
})
