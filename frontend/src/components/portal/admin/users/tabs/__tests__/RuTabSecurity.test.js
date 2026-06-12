import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

vi.mock('@/i18n', () => ({ getLocale: () => 'fr' }))

vi.mock('vue-i18n', () => ({
  useI18n: () => ({ t: k => k }),
}))

const fetchLoginHistory = vi.fn()

vi.mock('@/composables/portal/usePortalAdminUsers', () => ({
  usePortalAdminUsers: () => ({
    fetchLoginHistory,
    exportUserCsvUrl: () => '#',
    forceLogout: vi.fn(),
    resetPassword: vi.fn(),
    exportUser: vi.fn(),
  }),
}))

vi.mock('@/composables/useToast', () => ({ useToast: () => ({ showToast: vi.fn() }) }))
vi.mock('@/composables/useConfirm', () => ({
  useConfirm: () => vi.fn(() => Promise.resolve(true)),
}))
vi.mock('@/composables/portal/useFileDownload', () => ({ downloadJsonFile: vi.fn() }))

import RuTabSecurity from '@/components/portal/admin/users/tabs/RuTabSecurity.vue'

const LOAD_MORE_STUB = {
  props: ['show', 'loading'],
  template: '<button v-if="show" class="lm" @click="$emit(\'load\')">more</button>',
}

const loginPage = (start, n) =>
  Array.from({ length: n }, (_, i) => ({
    id: start + i,
    success: true,
    ip: null,
    user_agent: 'agent',
    created_at: null,
  }))

function mountTab() {
  return mount(RuTabSecurity, {
    props: { user: { id: 9, source: 'local', display_name: 'User' } },
    global: {
      stubs: {
        RuNotifyModal: true,
        RuPasswordResetModal: true,
        RuUserBadge: true,
        PortalLoadMore: LOAD_MORE_STUB,
      },
    },
  })
}

beforeEach(() => {
  fetchLoginHistory.mockReset()
})

describe('RuTabSecurity — login history load more', () => {
  it('appends the next login page and stops on a partial page', async () => {
    fetchLoginHistory
      .mockResolvedValueOnce({ items: loginPage(1, 100), has_more: true, next_cursor: 'cur-100' })
      .mockResolvedValueOnce({ items: loginPage(101, 5), has_more: false, next_cursor: null })

    const w = mountTab()
    await flushPromises()

    expect(w.findAll('.ru-feed-row')).toHaveLength(100)
    expect(w.find('.lm').exists()).toBe(true)

    await w.find('.lm').trigger('click')
    await flushPromises()

    expect(fetchLoginHistory).toHaveBeenLastCalledWith(9, { limit: 100, cursor: 'cur-100' })
    expect(w.findAll('.ru-feed-row')).toHaveLength(105)
    expect(w.find('.lm').exists()).toBe(false)
  })
})
