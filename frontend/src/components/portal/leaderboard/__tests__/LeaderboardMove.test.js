/**
 * Movement badge of a ranking row — arrow, number and tooltip, real translations.
 */
import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'

import en from '@/locales/en.json'
import fr from '@/locales/fr.json'
import LeaderboardMove from '../LeaderboardMove.vue'

vi.mock('vue-i18n', async importOriginal => {
  const actual = await importOriginal()
  const i18n = actual.createI18n({ legacy: false, locale: 'fr', messages: { fr, en } })
  return { ...actual, useI18n: () => ({ t: i18n.global.t }) }
})

const mountMove = props => mount(LeaderboardMove, { props })

describe('LeaderboardMove.vue', () => {
  it('shows a player who climbed in green, with the number of places', () => {
    const move = mountMove({ movement: 3 })
    expect(move.classes()).toContain('gc-lb-move--up')
    expect(move.text()).toBe('3')
    expect(move.attributes('title')).toContain('+3')
    expect(move.findAll('svg')).toHaveLength(1)
  })

  it('shows a player who fell in red, without the minus sign', () => {
    const move = mountMove({ movement: -2 })
    expect(move.classes()).toContain('gc-lb-move--down')
    expect(move.text()).toBe('2')
    expect(move.attributes('title')).toContain('-2')
  })

  it('shows a dash for a player who kept their rank', () => {
    const move = mountMove({ movement: 0 })
    expect(move.classes()).toContain('gc-lb-move--flat')
    expect(move.text()).toBe('—')
    expect(move.find('svg').exists()).toBe(false)
  })

  it('draws the arrow at the size of the row', () => {
    const move = mountMove({ movement: 1, size: 11 })
    expect(move.find('svg').attributes('width')).toBe('11')
  })

  it('shows nothing at all when the period has no previous one', () => {
    const move = mountMove({ movement: null, period: 'all' })
    expect(move.find('.gc-lb-move').exists()).toBe(false)
  })

  it.each([
    ['today', 2, '+2 place(s) depuis hier'],
    ['today', -2, '-2 place(s) depuis hier'],
    ['today', 0, "Même rang qu'hier"],
    ['week', 1, '+1 place(s) depuis la semaine dernière'],
    ['week', -1, '-1 place(s) depuis la semaine dernière'],
    ['week', 0, 'Même rang que la semaine dernière'],
    ['month', 4, '+4 place(s) depuis le mois dernier'],
    ['month', -4, '-4 place(s) depuis le mois dernier'],
    ['month', 0, 'Même rang que le mois dernier'],
  ])('on %s, %i reads "%s"', (period, movement, tooltip) => {
    expect(mountMove({ movement, period }).attributes('title')).toBe(tooltip)
  })

  it('compares with last month where no period is given', () => {
    expect(mountMove({ movement: 0 }).attributes('title')).toBe('Même rang que le mois dernier')
  })
})
