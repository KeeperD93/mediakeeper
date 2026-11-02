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
})
