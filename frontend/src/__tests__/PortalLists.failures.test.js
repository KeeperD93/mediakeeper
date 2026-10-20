/**
 * A failed list action says why: the list code the server gave (muted,
 * list full…) when known, else the action that failed. Never silent.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'

const mocks = vi.hoisted(() => ({
  showToast: vi.fn(),
  fetchMyLists: vi.fn(),
  deleteList: vi.fn(),
  createList: vi.fn(),
}))

vi.mock('vue-i18n', () => ({ useI18n: () => ({ t: key => key }) }))
// The list's own reason when its scope words it, else the action that failed.
vi.mock('@/composables/useApi', () => ({
  resolveScopedError: (scope, code, fallbackKey) =>
    code === 'owner_muted' ? `${scope}.${code}` : fallbackKey,
}))
vi.mock('@/composables/useToast', () => ({ useToast: () => ({ showToast: mocks.showToast }) }))
vi.mock('@/composables/useConfirm', () => ({ useConfirm: () => async () => true }))
vi.mock('@/composables/portal/usePortalAuth', () => ({
  usePortalAuth: () => ({ profile: ref({ role: 'viewer' }) }),
}))
vi.mock('@/composables/portal/usePortalLists', () => ({
  usePortalLists: () => ({
    lists: ref([{ id: 1, name: 'Sample list' }]),
    publicLists: ref([]),
    publicHasMore: ref(false),
    publicCursor: ref(null),
    fetchMyLists: mocks.fetchMyLists,
    fetchPublicLists: vi.fn(),
    deleteList: mocks.deleteList,
    createList: mocks.createList,
    exportUrl: () => '#',
  }),
}))
vi.mock('@/components/portal/lists/ListRow.vue', () => ({
  default: { name: 'ListRow', props: ['lst'], template: '<div />' },
}))
vi.mock('@/components/portal/lists/ListExpansion.vue', () => ({ default: { template: '<div />' } }))
vi.mock('@/components/portal/lists/ListFormModal.vue', () => ({
  default: { name: 'ListFormModal', props: ['busy'], template: '<div />' },
}))
vi.mock('@/components/portal/lists/AdminListsTab.vue', () => ({ default: { template: '<div />' } }))
vi.mock('@/components/common/TabStrip.vue', () => ({ default: { template: '<div />' } }))
vi.mock('@/assets/styles/portal/admin-rich-row-header.css', () => ({}))
vi.mock('@/assets/styles/portal/admin-rich-row.css', () => ({}))
vi.mock('@/assets/styles/portal/admin-rich-row-info.css', () => ({}))
vi.mock('@/assets/styles/portal/admin-rich-row-actions.css', () => ({}))

import PortalLists from '@/views/portal/PortalLists.vue'

async function deleteTheList(failure) {
  mocks.deleteList.mockRejectedValueOnce(failure)
  const w = mount(PortalLists)
  await flushPromises()
  w.findComponent({ name: 'ListRow' }).vm.$emit('delete', { id: 1 })
  await flushPromises()
}

describe('PortalLists — failures', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.spyOn(console, 'error').mockImplementation(() => {})
    mocks.fetchMyLists.mockResolvedValue([])
  })

  it('says the lists could not be loaded', async () => {
    mocks.fetchMyLists.mockRejectedValue(new Error('http_500'))

    mount(PortalLists)
    await flushPromises()

    expect(mocks.showToast).toHaveBeenCalledWith('common.apiError.loadFailed', 'err')
  })

  it("gives the list's own reason when the server names it", async () => {
    await deleteTheList(new Error('owner_muted'))

    expect(mocks.showToast).toHaveBeenCalledWith('portal.lists.errors.owner_muted', 'err')
  })

  it('else says which action failed', async () => {
    await deleteTheList(new Error('http_500'))

    expect(mocks.showToast).toHaveBeenCalledWith('common.apiError.deleteFailed', 'err')
  })

  it('sends the list form once while it saves', async () => {
    let finish
    mocks.createList.mockReturnValue(new Promise(resolve => (finish = resolve)))
    const w = mount(PortalLists)
    await flushPromises()
    const form = () => w.findComponent({ name: 'ListFormModal' })

    form().vm.$emit('submit', { name: 'New list' })
    form().vm.$emit('submit', { name: 'New list' })
    await flushPromises()

    expect(mocks.createList).toHaveBeenCalledTimes(1)
    expect(form().props('busy')).toBe(true)
    finish({ success: true })
    await flushPromises()
    expect(form().props('busy')).toBe(false)
  })
})
