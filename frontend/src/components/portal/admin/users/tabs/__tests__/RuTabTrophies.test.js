import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

vi.mock('@/i18n', () => ({ getLocale: () => 'fr' }))

vi.mock('vue-i18n', () => ({
  useI18n: () => ({
    t: (k, p) => (p ? `${k}:${JSON.stringify(p)}` : k),
    te: () => true,
  }),
}))

const fetchTrophies = vi.fn()
const fetchXpHistory = vi.fn()

vi.mock('@/composables/portal/usePortalAdminUsers', () => ({
  usePortalAdminUsers: () => ({ fetchTrophies, fetchXpHistory }),
}))

import RuTabTrophies from '@/components/portal/admin/users/tabs/RuTabTrophies.vue'

// Stub PortalLoadMore: render a clickable button only when `show`, so the
// test drives the tab's own load-more orchestration in isolation.
const LOAD_MORE_STUB = {
  props: ['show', 'loading'],
  template: '<button v-if="show" class="lm" @click="$emit(\'load\')">more</button>',
}

function mountTab() {
  return mount(RuTabTrophies, {
    props: { user: { id: 42, level: 1, xp: 55 }, activity: null },
    global: { stubs: { RuTrophyIcon: true, PortalLoadMore: LOAD_MORE_STUB } },
  })
}

const xpPage = (start, n) =>
  Array.from({ length: n }, (_, i) => ({
    id: start + i,
    action: 'daily_login',
    reference: null,
    xp: 5,
    created_at: null,
  }))

beforeEach(() => {
  fetchTrophies.mockReset()
  fetchXpHistory.mockReset()
  fetchTrophies.mockResolvedValue({
    unlocked: [],
    in_progress: [],
    unlocked_count: 0,
    in_progress_count: 0,
  })
})

describe('RuTabTrophies — XP ledger label', () => {
  it('replaces the generic achievement_unlocked label with the trophy name', async () => {
    fetchTrophies.mockResolvedValue({
      unlocked: [
        {
          id: 'curator-1',
          name_key: 'portal.trophies.curator_1.name',
          icon: 'star',
          xp_reward: 50,
        },
      ],
      in_progress: [],
      unlocked_count: 1,
      in_progress_count: 0,
    })
    fetchXpHistory.mockResolvedValue({
      items: [
        {
          id: 1,
          action: 'achievement_unlocked',
          reference: 'ach:curator-1',
          xp: 50,
          created_at: null,
        },
        { id: 2, action: 'daily_login', reference: null, xp: 5, created_at: null },
      ],
    })
    const w = mountTab()
    await flushPromises()

    const rows = w.findAll('.ru-feed-row .ru-feed-main').map(r => r.text())
    expect(rows[0]).toContain('portal.trophies.curator_1.name')
    expect(rows[0]).toContain('xpAction.achievementNamed')
    expect(rows[1]).toContain('xpAction.daily_login')
  })
})

describe('RuTabTrophies — XP history load more', () => {
  it('appends the next XP page and stops on a partial page', async () => {
    fetchXpHistory
      .mockResolvedValueOnce({ items: xpPage(1, 100) })
      .mockResolvedValueOnce({ items: xpPage(101, 10) })
    const w = mountTab()
    await flushPromises()

    expect(w.findAll('.ru-feed-row')).toHaveLength(100)
    expect(w.find('.lm').exists()).toBe(true) // full page → more available

    await w.find('.lm').trigger('click')
    await flushPromises()

    expect(fetchXpHistory).toHaveBeenLastCalledWith(42, { limit: 100, offset: 100 })
    expect(w.findAll('.ru-feed-row')).toHaveLength(110)
    expect(w.find('.lm').exists()).toBe(false) // partial page → no more
  })
})
