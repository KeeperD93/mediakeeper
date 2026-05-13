import { describe, it, expect, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

vi.mock('vue-i18n', () => ({
  useI18n: () => ({
    t: (k, p) => (p ? `${k}:${JSON.stringify(p)}` : k),
    te: () => true,
  }),
}))

vi.mock('@/composables/portal/usePortalAdminUsers', () => ({
  usePortalAdminUsers: () => ({
    fetchTrophies: vi.fn().mockResolvedValue({
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
    }),
    fetchXpHistory: vi.fn().mockResolvedValue({
      items: [
        {
          id: 1,
          action: 'achievement_unlocked',
          reference: 'ach:curator-1',
          xp: 50,
          created_at: '2026-05-13T10:00:00Z',
        },
        {
          id: 2,
          action: 'daily_login',
          reference: null,
          xp: 5,
          created_at: '2026-05-13T09:00:00Z',
        },
      ],
    }),
  }),
}))

import RuTabTrophies from '@/components/portal/admin/users/tabs/RuTabTrophies.vue'

describe('RuTabTrophies — XP ledger label', () => {
  it('replaces the generic achievement_unlocked label with the trophy name', async () => {
    const w = mount(RuTabTrophies, {
      props: { user: { id: 42, level: 1, xp: 55 }, activity: null },
      global: {
        stubs: { RuTrophyIcon: true },
      },
    })
    await flushPromises()

    const rows = w.findAll('.ru-feed-row .ru-feed-main').map(r => r.text())
    expect(rows[0]).toContain('portal.trophies.curator_1.name')
    expect(rows[0]).toContain('xpAction.achievementNamed')
    expect(rows[1]).toContain('xpAction.daily_login')
  })
})
