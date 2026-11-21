/**
 * Portal admin → debug tools → watch XP recalculation: the simulation shows its facts,
 * each player's change, and nothing to do when nothing changes; applying asks first and
 * sends back the moment and the plan it showed; an uncertain apply, or one whose answer is
 * lost on the way, drops the simulation and reloads the players.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

const simulateWatchXp = vi.fn()
const applyWatchXp = vi.fn()
const confirm = vi.fn()
const showToast = vi.fn()
vi.mock('@/composables/portal/usePortalAdminDebug', () => ({
  usePortalAdminDebug: () => ({ simulateWatchXp, applyWatchXp }),
}))
vi.mock('@/composables/useConfirm', () => ({ useConfirm: () => confirm }))
vi.mock('@/composables/useToast', () => ({ useToast: () => ({ showToast }) }))
vi.mock('@/composables/useApi', () => ({
  resolveScopedError: (scope, code) => `${scope}.${code}`,
}))
vi.mock('vue-i18n', () => ({
  // An event of the list reads "name (titles, XP)"; other parameters follow their key.
  useI18n: () => ({
    t: (key, p) => {
      if (p?.titles !== undefined) return `${p.name} (${p.titles}, ${p.xp})`
      return p ? `${key} ${JSON.stringify(p)}` : key
    },
  }),
}))

import AdminDebugWatchXp from '@/components/portal/admin/AdminDebugWatchXp.vue'
import { TOAST_TYPE } from '@/constants/toast'

const SUMMARY = {
  as_of: '2026-03-10T12:00:00+00:00',
  plan: '0123456789abcdef',
  players: 4,
  players_changed: 2,
  watch_xp_before: 30,
  watch_xp_after: 63,
  rows_deleted: 1,
  rows_inserted: 2,
  levels_up: 0,
  levels_down: 1,
  max_level_loss: 1,
  lost: { no_end: 1, not_due: 1, no_stats: 2 },
  skipped: { no_account: 1, erased: 1, parallel: 3 },
  namesakes: 1,
  events: [
    { name: 'Test Event', enabled: true, titles: 1, bonus_xp: 8 },
    { name: 'Test Event Off', enabled: false, titles: 2, bonus_xp: 22 },
    { name: 'Test Event Elsewhere', enabled: true, titles: 0, bonus_xp: 0 },
  ],
  leaders_changed: ['2026-03'],
  competitor_new: {},
  competitor_unjustified: {},
  rows: [{ user_id: 1, name: 'Alice', xp: 10, xp_after: 40, level: 1, level_after: 1 }],
}

const button = (wrapper, label) => wrapper.findAll('button').find(b => b.text() === label)

async function simulated(summary = SUMMARY) {
  simulateWatchXp.mockResolvedValue(summary)
  const wrapper = mount(AdminDebugWatchXp)
  await button(wrapper, 'portal.admin.debug.watchXpSimulate').trigger('click')
  await flushPromises()
  return wrapper
}

describe('AdminDebugWatchXp', () => {
  beforeEach(() => vi.clearAllMocks())

  it('shows the facts of the simulation and each player who changes', async () => {
    const text = (await simulated()).text()
    expect(text).toContain('"players":2,"total":4,"before":30,"after":63')
    expect(text).toContain('"lost":4,"noEnd":2,"stats":2')
    expect(text).toContain('"noAccount":2,"notEarning":0,"excluded":0,"cooldown":0,"parallel":3')
    expect(text).toContain('"events":"Test Event (1, 8)","ignored":"Test Event Off (2, 22)"')
    expect(text).not.toContain('Elsewhere')
    expect(text).toContain('"n":1')
    expect(text).toContain('Alice')
    expect(text).toContain('"xp":10,"xpAfter":40')
  })

  it('says there is nothing to recalculate', async () => {
    const text = (await simulated({ ...SUMMARY, players_changed: 0, rows: [] })).text()
    expect(text).toContain('portal.admin.debug.watchXpNothing')
    expect(text).not.toContain('portal.admin.debug.watchXpPlayers')
  })

  it('reports a failed simulation', async () => {
    simulateWatchXp.mockRejectedValue(new Error('boom'))
    vi.spyOn(console, 'error').mockImplementation(() => {})
    const wrapper = mount(AdminDebugWatchXp)
    await button(wrapper, 'portal.admin.debug.watchXpSimulate').trigger('click')
    await flushPromises()
    expect(showToast).toHaveBeenCalledWith('portal.admin.debug.errorGeneric', TOAST_TYPE.ERR)
  })

  it('cannot apply before a simulation, nor when nothing changes', async () => {
    const apply = wrapper => button(wrapper, 'portal.admin.debug.watchXpApply')
    expect(apply(mount(AdminDebugWatchXp)).attributes('disabled')).toBeDefined()
    const nothing = await simulated({ ...SUMMARY, players_changed: 0, rows: [] })
    expect(apply(nothing).attributes('disabled')).toBeDefined()
  })

  it('sends back the moment and the plan it showed once confirmed', async () => {
    confirm.mockResolvedValue(true)
    applyWatchXp.mockResolvedValue({
      plan: SUMMARY.plan,
      backup: 'mediakeeper_backup_20260310_120000_watch_xp_recalc.zip',
      applied: { players: 2, rows_deleted: 1, rows_inserted: 2 },
    })
    const wrapper = await simulated()
    await button(wrapper, 'portal.admin.debug.watchXpApply').trigger('click')
    await flushPromises()

    expect(confirm).toHaveBeenCalledWith({
      title: 'common.confirmTitle.action',
      message: 'portal.admin.debug.watchXpConfirm {"players":2}',
      variant: 'danger',
    })
    expect(applyWatchXp).toHaveBeenCalledWith(SUMMARY.as_of, SUMMARY.plan)
    const done =
      'portal.admin.debug.watchXpApplied ' +
      '{"players":2,"name":"mediakeeper_backup_20260310_120000_watch_xp_recalc.zip"}'
    expect(showToast).toHaveBeenCalledWith(done, TOAST_TYPE.OK)
    expect(wrapper.text()).toContain(done)
    expect(wrapper.emitted('changed')).toHaveLength(1)
    expect(wrapper.text()).not.toContain('Alice') // the simulation it applied is gone
  })

  it('writes nothing when the admin backs out', async () => {
    confirm.mockResolvedValue(false)
    const wrapper = await simulated()
    await button(wrapper, 'portal.admin.debug.watchXpApply').trigger('click')
    await flushPromises()
    expect(applyWatchXp).not.toHaveBeenCalled()
    expect(wrapper.emitted('changed')).toBeUndefined()
  })

  it('names the reason of a refusal', async () => {
    confirm.mockResolvedValue(true)
    applyWatchXp.mockRejectedValue(new Error('plan_changed'))
    vi.spyOn(console, 'error').mockImplementation(() => {})
    const wrapper = await simulated()
    await button(wrapper, 'portal.admin.debug.watchXpApply').trigger('click')
    await flushPromises()
    expect(showToast).toHaveBeenCalledWith(
      'portal.admin.debug.watchXpErrors.plan_changed',
      TOAST_TYPE.ERR,
    )
    expect(wrapper.emitted('changed')).toBeUndefined()
    expect(wrapper.text()).toContain('Alice') // the simulation stays
  })

  it('drops the simulation and reloads the players after an uncertain apply', async () => {
    confirm.mockResolvedValue(true)
    applyWatchXp.mockRejectedValue(new Error('apply_uncertain'))
    vi.spyOn(console, 'error').mockImplementation(() => {})
    const wrapper = await simulated()
    await button(wrapper, 'portal.admin.debug.watchXpApply').trigger('click')
    await flushPromises()
    expect(showToast).toHaveBeenCalledWith(
      'portal.admin.debug.watchXpErrors.apply_uncertain',
      TOAST_TYPE.ERR,
    )
    expect(wrapper.emitted('changed')).toHaveLength(1)
    expect(wrapper.text()).not.toContain('Alice')
    const apply = button(wrapper, 'portal.admin.debug.watchXpApply')
    expect(apply.attributes('disabled')).toBeDefined()
  })

  it.each([
    ['the connection drops', new TypeError('Failed to fetch')],
    ['a relay answers 502', new Error('http_502')],
    ['a relay answers 503', new Error('http_503')],
    ['a relay answers 504', new Error('http_504')],
  ])('takes the apply as uncertain when %s', async (_, failure) => {
    confirm.mockResolvedValue(true)
    applyWatchXp.mockRejectedValue(failure)
    vi.spyOn(console, 'error').mockImplementation(() => {})
    const wrapper = await simulated()
    await button(wrapper, 'portal.admin.debug.watchXpApply').trigger('click')
    await flushPromises()
    expect(showToast).toHaveBeenCalledWith(
      'portal.admin.debug.watchXpErrors.apply_uncertain',
      TOAST_TYPE.ERR,
    )
    expect(wrapper.emitted('changed')).toHaveLength(1)
    expect(wrapper.text()).not.toContain('Alice')
  })

  it('keeps an error the server answered as a failure', async () => {
    confirm.mockResolvedValue(true)
    applyWatchXp.mockRejectedValue(new Error('http_500'))
    vi.spyOn(console, 'error').mockImplementation(() => {})
    const wrapper = await simulated()
    await button(wrapper, 'portal.admin.debug.watchXpApply').trigger('click')
    await flushPromises()
    expect(showToast).toHaveBeenCalledWith(
      'portal.admin.debug.watchXpErrors.http_500',
      TOAST_TYPE.ERR,
    )
    expect(wrapper.emitted('changed')).toBeUndefined()
    expect(wrapper.text()).toContain('Alice')
  })

  it('says nothing on its way to the login page', async () => {
    confirm.mockResolvedValue(true)
    applyWatchXp.mockResolvedValue(null)
    const wrapper = await simulated()
    await button(wrapper, 'portal.admin.debug.watchXpApply').trigger('click')
    await flushPromises()
    expect(showToast).not.toHaveBeenCalled()
    expect(wrapper.emitted('changed')).toBeUndefined()
    expect(wrapper.text()).toContain('Alice')
  })
})
