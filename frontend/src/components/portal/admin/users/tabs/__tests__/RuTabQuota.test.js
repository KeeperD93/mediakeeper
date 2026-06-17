/**
 * Covers the #447 guard: a blank required numeric field must disable Save (no
 * silent backend rejection), in both manual (max_allowed) and auto (auto_min/
 * auto_max) modes, while a valid form still saves the expected payload.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

const patchQuota = vi.fn()
vi.mock('@/composables/portal/usePortalAdminUsers', () => ({
  usePortalAdminUsers: () => ({ patchQuota }),
}))
const showToast = vi.fn()
vi.mock('@/composables/useToast', () => ({ useToast: () => ({ showToast }) }))
// Partial mock: keep createI18n (used transitively via @/utils/datetime → @/i18n);
// only stub the component's script-level useI18n.
vi.mock('vue-i18n', async importOriginal => ({
  ...(await importOriginal()),
  useI18n: () => ({ t: k => k }),
}))

import RuTabQuota from '@/components/portal/admin/users/tabs/RuTabQuota.vue'
import { QUOTA_MODE } from '@/constants/portalAdminUsers'

function mountTab(quota) {
  return mount(RuTabQuota, {
    props: { user: { id: 7, quota } },
    global: { stubs: { AutoQuotaHelp: true } },
  })
}

const BASE = {
  max_allowed: 5,
  unlimited: false,
  auto_approve: false,
  auto_min: 2,
  auto_max: 15,
}

beforeEach(() => {
  patchQuota.mockReset().mockResolvedValue({ success: true })
  showToast.mockReset()
})

describe('RuTabQuota — blank-field save guard (#447)', () => {
  it('disables Save when the manual cap is cleared', async () => {
    const w = mountTab({ ...BASE, mode: QUOTA_MODE.MANUAL })
    await flushPromises()
    const btn = w.get('.ru-btn--primary')
    expect(btn.element.disabled).toBe(false)

    await w.get('input[type="number"]').setValue('')
    expect(btn.element.disabled).toBe(true)
    w.unmount()
  })

  it('disables Save when an auto bound is cleared', async () => {
    const w = mountTab({ ...BASE, mode: QUOTA_MODE.AUTO })
    await flushPromises()
    const btn = w.get('.ru-btn--primary')
    expect(btn.element.disabled).toBe(false)

    await w.findAll('input[type="number"]')[0].setValue('') // auto_min
    expect(btn.element.disabled).toBe(true)
    w.unmount()
  })

  it('saves the manual payload when the form is valid', async () => {
    const w = mountTab({ ...BASE, mode: QUOTA_MODE.MANUAL })
    await flushPromises()

    await w.get('.ru-btn--primary').trigger('click')
    await flushPromises()

    expect(patchQuota).toHaveBeenCalledWith(7, {
      mode: QUOTA_MODE.MANUAL,
      auto_approve: false,
      unlimited: false,
      max_allowed: 5,
    })
    w.unmount()
  })
})
