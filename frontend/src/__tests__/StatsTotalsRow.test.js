/**
 * Statistics → top ribbon: the peak hour, which an instance without plays does not have.
 */
import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { reactive, ref } from 'vue'

const records = ref(null)
vi.mock('@/composables/useStats', () => ({
  useStats: () => ({
    totals: reactive({ plays: 0, transcodePct: 0, disabledUsers: 3 }),
    sparklinePlays: ref([]),
    sparklineDuration: ref([]),
    records,
    minimap24h: ref([]),
    ticksToDuration: () => '0',
  }),
}))
vi.mock('vue-i18n', () => ({ useI18n: () => ({ t: key => key }) }))

import StatsTotalsRow from '@/components/stats/StatsTotalsRow.vue'

describe('StatsTotalsRow', () => {
  it.each([
    [null, '—'],
    [0, '0h'],
    [21, '21h'],
  ])('shows a peak hour of %s as %s', (hour, shown) => {
    records.value = { peak_hour: hour, peak_hour_count: 0 }
    expect(mount(StatsTotalsRow).findAll('.rec-value').at(-1).text()).toBe(shown)
  })

  it('leaves the colons of the disabled-users and direct-play lines to the translation', () => {
    const w = mount(StatsTotalsRow)

    expect(w.find('.tot-user-breakdown .tot-sub').text()).toBe('stats.disabled 3')
    expect(w.findAll('.tot-sub').at(-1).text()).toBe('stats.directPlayPct:{"pct":"100.0"}')
  })
})
