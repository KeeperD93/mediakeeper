/**
 * Covers the auto-quota instance settings card: it loads the quota.auto.*
 * settings, disables Save when a field is emptied (no silent backend
 * rejection, cf. the RuTabQuota lesson), and PATCHes all six knobs on save.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

const apiGet = vi.fn()
const apiPatch = vi.fn()
vi.mock('@/composables/useApi', () => ({ useApi: () => ({ apiGet, apiPatch }) }))
vi.mock('vue-i18n', () => ({ useI18n: () => ({ t: k => k }) }))
vi.mock('lucide-vue-next', () => ({ Save: { name: 'SaveStub', template: '<i />' } }))

import AdminAutoQuotaSetting from '@/components/portal/admin/AdminAutoQuotaSetting.vue'

const SETTINGS = {
  'quota.auto.enabled': true,
  'quota.auto.min': 2,
  'quota.auto.max': 15,
  'quota.auto.window_days': 30,
  'quota.auto.grace_days': 14,
  'quota.auto.up_step': 2,
  'quota.auto.down_step': 1,
}

function buildCard() {
  return mount(AdminAutoQuotaSetting, {
    global: {
      mocks: { $t: k => k },
      stubs: { MkToggle: { template: '<button class="mk-toggle-stub" />' } },
    },
  })
}

describe('AdminAutoQuotaSetting', () => {
  beforeEach(() => {
    apiGet.mockReset().mockResolvedValue({ ...SETTINGS })
    apiPatch.mockReset().mockResolvedValue({ ...SETTINGS })
  })

  it('loads the instance settings and enables Save when the form is valid', async () => {
    const w = buildCard()
    await flushPromises()

    expect(apiGet).toHaveBeenCalledWith('/api/portal/admin/settings')
    const inputs = w.findAll('input[type="number"]')
    expect(inputs).toHaveLength(6)
    expect(inputs[0].element.value).toBe('2')
    expect(w.get('.pt-aq-save').element.disabled).toBe(false)

    w.unmount()
  })

  it('disables Save when a field is emptied (no silent save)', async () => {
    const w = buildCard()
    await flushPromises()

    await w.findAll('input[type="number"]')[0].setValue('')
    expect(w.get('.pt-aq-save').element.disabled).toBe(true)

    w.unmount()
  })

  it('PATCHes all six quota.auto.* knobs on save', async () => {
    const w = buildCard()
    await flushPromises()

    await w.get('.pt-aq-save').trigger('click')
    await flushPromises()

    expect(apiPatch).toHaveBeenCalledWith('/api/portal/admin/settings', {
      'quota.auto.min': 2,
      'quota.auto.max': 15,
      'quota.auto.window_days': 30,
      'quota.auto.grace_days': 14,
      'quota.auto.up_step': 2,
      'quota.auto.down_step': 1,
    })

    w.unmount()
  })
})
