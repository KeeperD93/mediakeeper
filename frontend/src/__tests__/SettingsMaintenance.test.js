/**
 * Covers the maintenance settings panel error handling: a failed initial load,
 * toggle or text save each surface a toast instead of silently swallowing the
 * rejection in a catch-less try/finally (cf. the auto-quota card).
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

const apiGet = vi.fn()
const apiPatch = vi.fn()
const showToast = vi.fn()
vi.mock('@/composables/useApi', () => ({ useApi: () => ({ apiGet, apiPatch }) }))
vi.mock('@/composables/useToast', () => ({ useToast: () => ({ showToast }) }))
vi.mock('vue-i18n', () => ({ useI18n: () => ({ t: k => k, locale: { value: 'fr' } }) }))

import SettingsMaintenance from '@/components/portal/admin/settings/panels/SettingsMaintenance.vue'

const STATE = { enabled: true, text_fr: 'x', text_en: 'y' }

function buildPanel() {
  return mount(SettingsMaintenance, {
    global: {
      mocks: { $t: k => k },
      stubs: {
        MkToggle: {
          props: ['modelValue'],
          template:
            '<button class="mk-toggle-stub" @click="$emit(\'update:model-value\', !modelValue)" />',
        },
        SettingsSection: { template: '<div><slot /></div>' },
        SettingRow: { template: '<div><slot /></div>' },
      },
    },
  })
}

describe('SettingsMaintenance', () => {
  beforeEach(() => {
    apiGet.mockReset().mockResolvedValue({ ...STATE })
    apiPatch.mockReset().mockResolvedValue({ ...STATE })
    showToast.mockClear()
  })

  it('shows a toast when the initial load fails', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
    apiGet.mockRejectedValueOnce(new Error('500'))
    const w = buildPanel()
    await flushPromises()

    expect(showToast).toHaveBeenCalled()
    w.unmount()
  })

  it('shows a toast when saving the text fails', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
    apiPatch.mockRejectedValueOnce(new Error('500'))
    const w = buildPanel()
    await flushPromises() // load resolves, enabled=true -> textarea + save button shown

    await w.get('.set-bar-btn').trigger('click') // saveText
    await flushPromises()

    expect(showToast).toHaveBeenCalled()
    w.unmount()
  })

  it('shows a toast when toggling fails', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
    apiPatch.mockRejectedValueOnce(new Error('500'))
    const w = buildPanel()
    await flushPromises()

    await w.get('.mk-toggle-stub').trigger('click') // onToggle
    await flushPromises()

    expect(showToast).toHaveBeenCalled()
    w.unmount()
  })
})
