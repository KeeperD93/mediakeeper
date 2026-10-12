/**
 * Settings → General: the update-check switch mirrors the server status,
 * saves through the shared composable, and is locked when the server
 * configuration forces the check off.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'

const status = ref(null)
const load = vi.fn()
const setEnabled = vi.fn()
vi.mock('@/composables/useUpdateCheck', () => ({
  useUpdateCheck: () => ({ status, load, setEnabled }),
}))
vi.mock('@/i18n', () => ({ getLocale: () => 'fr', setLocale: vi.fn(), AVAILABLE_LOCALES: [] }))

import ParamsGeneralTab from '@/components/settings/ParamsGeneralTab.vue'

const updateSwitch = w => w.get('[role="switch"]')

describe('ParamsGeneralTab — update check', () => {
  beforeEach(() => {
    status.value = { enabled: true, locked: false }
    load.mockClear()
    setEnabled.mockReset().mockResolvedValue(undefined)
  })

  it('reflects the server status and saves a change', async () => {
    const w = mount(ParamsGeneralTab)
    expect(load).toHaveBeenCalledTimes(1)
    expect(updateSwitch(w).attributes('aria-checked')).toBe('true')
    await updateSwitch(w).trigger('click')
    await flushPromises()
    expect(setEnabled).toHaveBeenCalledWith(false)
  })

  it('locks the switch when the server configuration forces the check off', () => {
    status.value = { enabled: false, locked: true }
    const w = mount(ParamsGeneralTab)
    expect(updateSwitch(w).attributes('disabled')).toBeDefined()
    expect(w.text()).toContain('settings.updateCheckLocked')
  })
})
