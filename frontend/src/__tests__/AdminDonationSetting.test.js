/**
 * Covers the donation settings card error handling: a failed toggle reverts
 * the optimistic switch and surfaces a toast, and a failed save surfaces a
 * toast — the previous try/finally swallowed both (cf. the auto-quota card).
 * Mocks the HTTP layer (useApi) and lets the real useDonationAdmin run.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

const apiGet = vi.fn()
const apiPatch = vi.fn()
const loadDonation = vi.fn()
const showToast = vi.fn()
vi.mock('@/composables/useApi', () => ({ useApi: () => ({ apiGet, apiPatch }) }))
vi.mock('@/composables/useDonationConfig', () => ({ useDonationConfig: () => ({ loadDonation }) }))
vi.mock('@/composables/useToast', () => ({ useToast: () => ({ showToast }) }))
vi.mock('vue-i18n', () => ({ useI18n: () => ({ t: k => k }) }))
vi.mock('lucide-vue-next', () => ({ Save: { name: 'SaveStub', template: '<i />' } }))

import AdminDonationSetting from '@/components/portal/admin/AdminDonationSetting.vue'

const SETTINGS = {
  'donation.enabled': true,
  'donation.url': 'https://example.test',
  'donation.message': 'hi',
  'donation.button_label': 'Tip',
}

function buildCard() {
  return mount(AdminDonationSetting, {
    global: {
      mocks: { $t: k => k },
      stubs: {
        MkToggle: {
          props: ['modelValue'],
          template:
            '<button class="mk-toggle-stub" @click="$emit(\'update:model-value\', !modelValue)" />',
        },
        HelpEditor: true,
      },
    },
  })
}

describe('AdminDonationSetting', () => {
  beforeEach(() => {
    apiGet.mockReset().mockResolvedValue({ ...SETTINGS })
    apiPatch.mockReset().mockResolvedValue({ ...SETTINGS })
    loadDonation.mockReset().mockResolvedValue()
    showToast.mockClear()
  })

  it('reverts the optimistic toggle and shows a toast when the toggle save fails', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
    apiPatch.mockRejectedValueOnce(new Error('500'))
    const w = buildCard()
    await flushPromises()
    expect(w.find('.pt-don-config').exists()).toBe(true) // enabled=true from load

    await w.get('.mk-toggle-stub').trigger('click') // optimistic flip to false
    await flushPromises()

    expect(showToast).toHaveBeenCalled()
    expect(w.find('.pt-don-config').exists()).toBe(true) // reverted -> still shown

    w.unmount()
  })

  it('shows a toast when the save request fails', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
    apiPatch.mockRejectedValueOnce(new Error('500'))
    const w = buildCard()
    await flushPromises()

    await w.get('.pt-don-save').trigger('click')
    await flushPromises()

    expect(showToast).toHaveBeenCalled()

    w.unmount()
  })
})
