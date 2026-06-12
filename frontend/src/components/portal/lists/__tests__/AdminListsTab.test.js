import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'

vi.mock('vue-i18n', () => ({
  useI18n: () => ({ t: (k, p) => (p ? `${k}:${JSON.stringify(p)}` : k) }),
}))

const moderationListsRef = ref([])
const moderationTotalRef = ref(0)
const moderationHasMoreRef = ref(false)
const moderationCursorRef = ref(null)
const fetchModerationLists = vi.fn()

vi.mock('@/composables/portal/usePortalLists', () => ({
  usePortalLists: () => ({
    moderationLists: moderationListsRef,
    moderationTotal: moderationTotalRef,
    moderationHasMore: moderationHasMoreRef,
    moderationCursor: moderationCursorRef,
    fetchModerationLists,
    adminUndelete: vi.fn(() => Promise.resolve({ success: true })),
    adminHardDelete: vi.fn(() => Promise.resolve({ success: true })),
    adminMuteOwner: vi.fn(() => Promise.resolve({ success: true })),
  }),
}))

vi.mock('@/composables/useToast', () => ({ useToast: () => ({ showToast: vi.fn() }) }))
vi.mock('@/composables/useConfirm', () => ({
  useConfirm: () => vi.fn(() => Promise.resolve(true)),
}))

import AdminListsTab from '@/components/portal/lists/AdminListsTab.vue'

const LOAD_MORE_STUB = {
  props: ['show', 'loading'],
  template: '<button v-if="show" class="lm" @click="$emit(\'load\')">more</button>',
}
const STUBS = { MkSpinner: true, PortalLoadMore: LOAD_MORE_STUB }

const row = (id, extra = {}) => ({
  id,
  name: `List ${id}`,
  privacy: 'public_readonly',
  item_count: 0,
  owner_muted: false,
  is_deleted: false,
  ...extra,
})
const page = (start, n) => Array.from({ length: n }, (_, i) => row(start + i))

beforeEach(() => {
  moderationListsRef.value = []
  moderationTotalRef.value = 0
  moderationHasMoreRef.value = false
  moderationCursorRef.value = null
  fetchModerationLists.mockReset()
})

describe('AdminListsTab — moderation', () => {
  it('shows a soft-deleted list with an undelete action', async () => {
    fetchModerationLists.mockImplementation(() => {
      moderationListsRef.value = [row(1), row(2, { is_deleted: true })]
      moderationHasMoreRef.value = false
      return Promise.resolve()
    })
    const w = mount(AdminListsTab, { global: { stubs: STUBS } })
    await flushPromises()

    expect(w.findAll('.adm-table tbody tr')).toHaveLength(2)
    // The deleted row is flagged and exposes the undelete button — the whole
    // point of routing moderation through the admin-only feed.
    expect(w.find('.adm-row--deleted').exists()).toBe(true)
    expect(w.findAll('.adm-btn').some(b => b.text().includes('undelete'))).toBe(true)
  })

  it('load more appends the next moderation page via the previous cursor', async () => {
    fetchModerationLists.mockImplementation(({ cursor = null, append = false } = {}) => {
      const p = cursor === null ? page(1, 50) : page(51, 10)
      moderationListsRef.value = append ? [...moderationListsRef.value, ...p] : p
      moderationHasMoreRef.value = cursor === null
      moderationCursorRef.value = cursor === null ? 'cur-50' : null
      return Promise.resolve()
    })
    const w = mount(AdminListsTab, { global: { stubs: STUBS } })
    await flushPromises()

    expect(w.findAll('.adm-table tbody tr')).toHaveLength(50)
    expect(w.find('.lm').exists()).toBe(true)

    await w.find('.lm').trigger('click')
    await flushPromises()

    expect(fetchModerationLists).toHaveBeenLastCalledWith({
      limit: 50,
      cursor: 'cur-50',
      append: true,
    })
    expect(w.findAll('.adm-table tbody tr')).toHaveLength(60)
    expect(w.find('.lm').exists()).toBe(false)
  })
})
