/**
 * Favourite day tile: one bar per day of the week, whatever the language writes
 * for its initials (two « M » in French, two « T » and two « S » in English).
 */
import { afterEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'

import StatsGenreCard from '../StatsGenreCard.vue'

vi.mock('vue-i18n', async importOriginal => ({
  ...(await importOriginal()),
  useI18n: () => ({ t: key => key }),
}))

const week = labels => labels.map((label, i) => ({ label, pct: i * 10, top: i === 6 }))
const FRENCH = week(['L', 'M', 'M', 'J', 'V', 'S', 'D'])
const ENGLISH = week(['M', 'T', 'W', 'T', 'F', 'S', 'S'])

function mountCard(weekData) {
  return mount(StatsGenreCard, {
    props: {
      stats: {},
      weekData,
      topDay: 'Sunday',
      genreName: id => id,
      genreColor: {},
      genreEmoji: {},
    },
  })
}

const dayLabels = wrapper => wrapper.findAll('.gc-daybar-wrap .gc-daylabel').map(l => l.text())

describe('StatsGenreCard.vue — favourite day', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('draws the seven English days when the language changes, without a key clash', async () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {})
    const wrapper = mountCard(FRENCH)

    await wrapper.setProps({ weekData: ENGLISH })

    expect(wrapper.findAll('.gc-daybar-wrap')).toHaveLength(7)
    expect(dayLabels(wrapper)).toEqual(['M', 'T', 'W', 'T', 'F', 'S', 'S'])
    expect(warn.mock.calls.flat().join(' ')).not.toContain('Duplicate keys')
  })
})
