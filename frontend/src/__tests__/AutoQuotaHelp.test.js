/**
 * Covers the shared auto-quota help affordance: collapsed by default, the
 * toggle reveals the explanation and the 5-signal scoring table.
 */
import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'

vi.mock('vue-i18n', () => ({ useI18n: () => ({ t: k => k }) }))
vi.mock('lucide-vue-next', () => ({ HelpCircle: { name: 'HelpStub', template: '<i />' } }))

import AutoQuotaHelp from '@/components/portal/admin/AutoQuotaHelp.vue'

function mountHelp() {
  return mount(AutoQuotaHelp, { global: { mocks: { $t: k => k } } })
}

describe('AutoQuotaHelp', () => {
  it('is collapsed by default and reveals the signals table on toggle', async () => {
    const w = mountHelp()
    expect(w.find('.aqh-panel').exists()).toBe(false)

    await w.get('.aqh-toggle').trigger('click')
    expect(w.find('.aqh-panel').exists()).toBe(true)
    expect(w.findAll('.aqh-table tbody tr')).toHaveLength(5)

    await w.get('.aqh-toggle').trigger('click')
    expect(w.find('.aqh-panel').exists()).toBe(false)
    w.unmount()
  })
})
