import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'

vi.mock('@/composables/portal/usePortalChat', () => ({
  usePortalChat: () => ({ unreadCount: { value: 0 }, markRead: vi.fn() }),
}))

vi.mock('@/composables/portal/usePortalAuth', () => ({
  usePortalAuth: () => ({ profile: { value: { chat_enabled: true } } }),
}))

import HomeFab from '@/components/portal/HomeFab.vue'

describe('HomeFab', () => {
  it('does not render a Promotion sub-button when expanded', async () => {
    const w = mount(HomeFab, {
      global: {
        stubs: {
          ChatPanel: true,
          EventCreateModal: true,
          'transition-group': { template: '<div><slot /></div>' },
        },
      },
    })
    await w.find('.pt-fab-main').trigger('click')

    const titles = w.findAll('button').map(b => b.attributes('title') || '')
    expect(titles.some(t => t.includes('portal.promotion'))).toBe(false)
    expect(w.findAll('.pt-fab-btn--disabled')).toHaveLength(0)
  })
})
