/**
 * Portal admin → debug tools → watch XP recalculation: the simulation shows its facts,
 * each player's change, and nothing to do when nothing changes.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

const simulateWatchXp = vi.fn()
const showToast = vi.fn()
vi.mock('@/composables/portal/usePortalAdminDebug', () => ({
  usePortalAdminDebug: () => ({ simulateWatchXp }),
}))
vi.mock('@/composables/useToast', () => ({ useToast: () => ({ showToast }) }))
vi.mock('vue-i18n', () => ({
  // An event of the list reads "name (titles, XP)"; any other key reads as itself.
  useI18n: () => ({ t: (key, p) => (p ? `${p.name} (${p.titles}, ${p.xp})` : key) }),
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
})
