/**
 * Portal admin → debug tools → fix of the trophies counted in UTC: the simulation shows
 * its totals, applying asks first and sends back the zone and the plan it showed.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

const simulateZoneCorrection = vi.fn()
const applyZoneCorrection = vi.fn()
const confirm = vi.fn()
const showToast = vi.fn()
vi.mock('@/composables/portal/usePortalAdminDebug', () => ({
  usePortalAdminDebug: () => ({ simulateZoneCorrection, applyZoneCorrection }),
}))
vi.mock('@/composables/useConfirm', () => ({ useConfirm: () => confirm }))
vi.mock('@/composables/useToast', () => ({ useToast: () => ({ showToast }) }))
vi.mock('@/composables/useApi', () => ({
  resolveScopedError: (scope, code) => `${scope}.${code}`,
}))
vi.mock('vue-i18n', () => ({ useI18n: () => ({ t: key => key }) }))
vi.mock('@/utils/datetime', () => ({ localizedDateTime: () => '1 February 2026' }))

import AdminDebugZoneCorrection from '@/components/portal/admin/AdminDebugZoneCorrection.vue'
import { TOAST_TYPE } from '@/constants/toast'

const SUMMARY = {
  timezone: 'Europe/Paris',
  zone_saved_at: '2026-02-01T12:00:00+00:00',
  plan: '0123456789abcdef',
  players: 19,
  players_affected: 7,
  players_failed: 0,
  removals: [
    {
      achievement_id: 'secret_early_bird',
      name_key: 'portal.achievements.secretEarlyBird',
      direct: 4,
      cascade: 0,
      imported: 0,
    },
  ],
  removed_total: 8,
  removed_imported: 0,
  xp_removed: 350,
  players_losing_level: 1,
  max_level_loss: 1,
  decorations_removed: 0,
  kept_nowhere: [{ achievement_id: 'secret_indecisive', name_key: 'x', count: 1 }],
  kept_gifts: [],
  competitor_months: { changed: 0, created: 0 },
  king_months: { changed: 0, created: 0 },
}
const APPLIED = {
  ...SUMMARY,
  backup: 'mediakeeper_backup_20260201_120000_zone_correction.zip',
  applied: { players: 7, removed: 8, xp_removed: 350, failed: 0, changed: 0 },
}

const button = (wrapper, label) => wrapper.findAll('button').find(b => b.text() === label)

async function simulated() {
  simulateZoneCorrection.mockResolvedValue(SUMMARY)
  const wrapper = mount(AdminDebugZoneCorrection)
  await button(wrapper, 'portal.admin.debug.zoneSimulate').trigger('click')
  await flushPromises()
  return wrapper
}

describe('AdminDebugZoneCorrection', () => {
  beforeEach(() => vi.clearAllMocks())

  it('cannot apply before a simulation', () => {
    const wrapper = mount(AdminDebugZoneCorrection)
    expect(button(wrapper, 'portal.admin.debug.zoneApply').attributes('disabled')).toBeDefined()
  })

  it('shows the totals and each trophy of the simulation', async () => {
    const wrapper = await simulated()
    expect(wrapper.text()).toContain('"removed":8,"players":7,"total":19,"xp":350')
    expect(wrapper.text()).toContain('portal.achievements.secretEarlyBird')
    expect(wrapper.text()).toContain('"nowhere":1,"gifts":0')
    expect(button(wrapper, 'portal.admin.debug.zoneApply').attributes('disabled')).toBeUndefined()
  })

  it('sends back the zone and the plan it showed once confirmed', async () => {
    const wrapper = await simulated()
    confirm.mockResolvedValue(true)
    applyZoneCorrection.mockResolvedValue(APPLIED)
    await button(wrapper, 'portal.admin.debug.zoneApply').trigger('click')
    await flushPromises()
    expect(applyZoneCorrection).toHaveBeenCalledWith('Europe/Paris', '0123456789abcdef')
    expect(wrapper.text()).toContain(APPLIED.backup)
    expect(wrapper.text()).not.toContain('zoneAppliedChanged')
    expect(wrapper.emitted('changed')).toHaveLength(1)
  })

  it('says how many players were left as they were', async () => {
    const wrapper = await simulated()
    confirm.mockResolvedValue(true)
    applyZoneCorrection.mockResolvedValue({
      ...APPLIED,
      applied: { ...APPLIED.applied, changed: 2 },
    })
    await button(wrapper, 'portal.admin.debug.zoneApply').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('zoneAppliedChanged')
    expect(wrapper.text()).toContain('"n":2')
  })

  it('writes nothing when the admin backs out', async () => {
    const wrapper = await simulated()
    confirm.mockResolvedValue(false)
    await button(wrapper, 'portal.admin.debug.zoneApply').trigger('click')
    await flushPromises()
    expect(applyZoneCorrection).not.toHaveBeenCalled()
  })

  it('names the reason of a refusal', async () => {
    const wrapper = await simulated()
    confirm.mockResolvedValue(true)
    applyZoneCorrection.mockRejectedValue(new Error('plan_changed'))
    vi.spyOn(console, 'error').mockImplementation(() => {})
    await button(wrapper, 'portal.admin.debug.zoneApply').trigger('click')
    await flushPromises()
    expect(showToast).toHaveBeenCalledWith(
      'portal.admin.debug.zoneErrors.plan_changed',
      TOAST_TYPE.ERR,
    )
    expect(wrapper.emitted('changed')).toBeUndefined()
  })
})
