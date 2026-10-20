/**
 * Request notifications in the bell (approved, available, rejected) open
 * the title's page.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

const mocks = vi.hoisted(() => ({ apiGet: vi.fn(), apiPost: vi.fn(), push: vi.fn() }))

vi.mock('vue-i18n', async importOriginal => ({
  ...(await importOriginal()),
  useI18n: () => ({ t: key => key }),
}))
vi.mock('vue-router', () => ({ useRouter: () => ({ push: mocks.push }) }))
vi.mock('@/composables/useApi', () => ({
  useApi: () => ({ apiGet: mocks.apiGet, apiPost: mocks.apiPost }),
}))

import NotificationBell from '@/components/portal/NotificationBell.vue'

function buildBell() {
  return mount(NotificationBell, {
    attachTo: document.body,
    global: {
      stubs: { EventDetailModal: true, PortalLoadMore: true },
      mocks: { $t: key => key },
    },
  })
}

describe('NotificationBell — request notifications', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    mocks.apiPost.mockResolvedValue({})
  })

  it.each(['request_approved', 'request_available', 'request_rejected'])(
    '%s opens the title page',
    async type => {
      mocks.apiGet.mockResolvedValue({
        items: [
          {
            id: 1,
            type,
            read: true,
            created_at: null,
            payload: { tmdb_id: 12345, media_type: 'movie', title: 'Test Movie' },
          },
        ],
        unread: 0,
        has_more: false,
        next_cursor: null,
      })
      const w = buildBell()
      await flushPromises()

      await w.get('.pt-bell').trigger('click')
      await flushPromises()
      document.querySelector('.pt-bell-item').click()
      await flushPromises()

      expect(mocks.push).toHaveBeenCalledWith({
        name: 'portal-media-detail',
        params: { type: 'movie', id: 12345 },
      })
      w.unmount()
    },
  )
})
