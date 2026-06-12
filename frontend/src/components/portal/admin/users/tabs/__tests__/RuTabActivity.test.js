import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

vi.mock('@/i18n', () => ({ getLocale: () => 'fr' }))

const fetchUserRequests = vi.fn()
const fetchUserTickets = vi.fn()

vi.mock('@/composables/portal/usePortalAdminUsers', () => ({
  usePortalAdminUsers: () => ({ fetchUserRequests, fetchUserTickets }),
}))

import RuTabActivity from '@/components/portal/admin/users/tabs/RuTabActivity.vue'

const LOAD_MORE_STUB = {
  props: ['show', 'loading'],
  template: '<button v-if="show" class="lm" @click="$emit(\'load\')">more</button>',
}

// The overview grid reads the ``activity`` prop; the request/ticket feeds
// (the paginated part) load through the mocked composable.
const ACTIVITY = {
  requests: { total: 0, pending: 0, available: 0 },
  tickets: { total: 0, open: 0 },
  lists: { total: 0 },
  ratings: { total: 0 },
  xp: { last_30_days: 0, total: 0 },
}

const reqPage = (start, n) =>
  Array.from({ length: n }, (_, i) => ({
    id: start + i,
    title: `Req ${start + i}`,
    status: 'pending',
    created_at: null,
  }))

function mountTab() {
  return mount(RuTabActivity, {
    props: { user: { id: 7 }, activity: ACTIVITY },
    global: { stubs: { RuUserBadge: true, PortalLoadMore: LOAD_MORE_STUB } },
  })
}

beforeEach(() => {
  fetchUserRequests.mockReset()
  fetchUserTickets.mockReset()
})

describe('RuTabActivity — feed load more', () => {
  it('loads more requests independently, via the previous page cursor', async () => {
    fetchUserRequests
      .mockResolvedValueOnce({ items: reqPage(1, 100), has_more: true, next_cursor: 'cur-100' })
      .mockResolvedValueOnce({ items: reqPage(101, 10), has_more: false, next_cursor: null })
    fetchUserTickets.mockResolvedValue({ items: [], has_more: false, next_cursor: null })

    const w = mountTab()
    await flushPromises()

    // Tickets empty → only the requests feed has rows + a load-more button.
    expect(w.findAll('.ru-feed-row')).toHaveLength(100)
    expect(w.findAll('.lm')).toHaveLength(1)

    await w.find('.lm').trigger('click')
    await flushPromises()

    expect(fetchUserRequests).toHaveBeenLastCalledWith(7, { limit: 100, cursor: 'cur-100' })
    expect(w.findAll('.ru-feed-row')).toHaveLength(110)
    expect(w.findAll('.lm')).toHaveLength(0) // partial page → no more
  })
})
