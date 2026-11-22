/**
 * Watch XP recalculation card, read with the real texts: one player, one loss and one
 * title linked by name read in the singular, in French and English, from the simulation
 * to the confirmation and the result.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createI18n } from 'vue-i18n'
import en from '@/locales/en.json'
import fr from '@/locales/fr.json'

const simulateWatchXp = vi.fn()
const applyWatchXp = vi.fn()
const confirm = vi.fn()
const showToast = vi.fn()
vi.mock('@/composables/portal/usePortalAdminDebug', () => ({
  usePortalAdminDebug: () => ({ simulateWatchXp, applyWatchXp }),
}))
vi.mock('@/composables/useConfirm', () => ({ useConfirm: () => confirm }))
vi.mock('@/composables/useToast', () => ({ useToast: () => ({ showToast }) }))

import AdminDebugWatchXp from '@/components/portal/admin/AdminDebugWatchXp.vue'

function summaryOf(n) {
  return {
    as_of: '2026-03-10T12:00:00+00:00',
    plan: '0123456789abcdef',
    players: 4,
    players_changed: n,
    watch_xp_before: 30,
    watch_xp_after: 40,
    levels_up: 0,
    levels_down: 0,
    max_level_loss: 0,
    lost: { no_end: n },
    skipped: {},
    namesakes: n,
    events: [],
    leaders_changed: [],
    rows: [{ user_id: 1, name: 'Alice', xp: 10, xp_after: 20, level: 1, level_after: 1 }],
  }
}

async function readThrough(locale, n) {
  const summary = summaryOf(n)
  simulateWatchXp.mockResolvedValue(summary)
  confirm.mockResolvedValue(true)
  applyWatchXp.mockResolvedValue({
    plan: summary.plan,
    backup: 'test_backup.zip',
    applied: { players: n, rows_deleted: n, rows_inserted: n },
  })
  const i18n = createI18n({ legacy: false, locale, messages: { fr, en } })
  const wrapper = mount(AdminDebugWatchXp, {
    global: { plugins: [i18n], mocks: { $t: i18n.global.t } },
  })
  const [simulate, apply] = wrapper.findAll('button')
  await simulate.trigger('click')
  await flushPromises()
  const simulated = wrapper.text()
  await apply.trigger('click')
  await flushPromises()
  const read = {
    simulated,
    asked: confirm.mock.calls[0][0].message,
    done: showToast.mock.calls[0][0],
  }
  wrapper.unmount()
  return read
}

describe('AdminDebugWatchXp plural forms', () => {
  beforeEach(() => vi.clearAllMocks())

  it.each([
    [
      'fr',
      1,
      ['1 joueur concerné sur 4', '1 joueur perd toute son XP', '1 titre vu rattaché'],
      'de 1 joueur ?',
      'recalculée pour 1 joueur.',
    ],
    [
      'fr',
      2,
      ['2 joueurs concernés sur 4', '2 joueurs perdent toute leur XP', '2 titres vus rattachés'],
      'de 2 joueurs ?',
      'recalculée pour 2 joueurs.',
    ],
    [
      'en',
      1,
      ['1 player affected out of 4', '1 player loses all', '1 watched title linked'],
      'of 1 player?',
      'for 1 player.',
    ],
    [
      'en',
      2,
      ['2 players affected out of 4', '2 players lose all', '2 watched titles linked'],
      'of 2 players?',
      'for 2 players.',
    ],
  ])('in %s with %i', async (locale, n, facts, asked, done) => {
    const read = await readThrough(locale, n)
    for (const fact of facts) expect(read.simulated).toContain(fact)
    expect(read.asked).toContain(asked)
    expect(read.done).toContain(done)
  })
})
