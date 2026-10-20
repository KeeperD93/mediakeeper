/**
 * Adding a title to a list from its poster says why it failed: the list's
 * own reason when the server gives one (too many edits, list full…), else
 * the action that failed. A refresh that fails after a good add is not a
 * failed add, and a new list is created once however fast Save is clicked.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'

const h = vi.hoisted(() => ({
  addItems: vi.fn(),
  createList: vi.fn(),
  fetchMyLists: vi.fn(),
  showToast: vi.fn(),
  known: new Set(['portal.lists.errors.rate_limited', 'portal.lists.errors.owner_muted']),
}))

vi.mock('vue-i18n', () => ({ useI18n: () => ({ t: k => k }) }))
vi.mock('@/composables/useToast', () => ({ useToast: () => ({ showToast: h.showToast }) }))
// The list's own reason when its scope words it, nothing over a rate limit
// (its toast says it), else the action that failed.
vi.mock('@/composables/useApi', () => ({
  resolveScopedError: (scope, code, fallbackKey) => {
    if (h.known.has(`${scope}.${code}`)) return `${scope}.${code}`
    return code === 'rate_limited_notified' ? '' : fallbackKey
  },
}))
vi.mock('@/composables/portal/usePortalLists', () => ({
  usePortalLists: () => ({
    lists: ref([{ id: 1, name: 'My list', is_owner: true, privacy: 'private', item_count: 0 }]),
    publicLists: ref([]),
    fetchMyLists: h.fetchMyLists,
    fetchPublicLists: vi.fn().mockResolvedValue([]),
    addItems: h.addItems,
    createList: h.createList,
  }),
}))
vi.mock('@/components/portal/lists/ListFormModal.vue', () => ({
  default: { name: 'ListFormModal', props: ['busy'], template: '<div />' },
}))

import AddToListOverlay from '@/components/portal/lists/AddToListOverlay.vue'

const MEDIA = { tmdb_id: 900001, media_type: 'movie', title: 'Sample Movie' }
const errors = () => h.showToast.mock.calls.filter(([message, type]) => type === 'err' && message)

const mountOverlay = (open = true) => mount(AddToListOverlay, { props: { open, media: MEDIA } })

async function pickTheList() {
  const w = mountOverlay()
  await w.find('.atl-row').trigger('click')
  await flushPromises()
  return w
}

async function createThenAdd() {
  const w = mountOverlay()
  w.findComponent({ name: 'ListFormModal' }).vm.$emit('submit', { name: 'New list' })
  await flushPromises()
  return w
}

describe('AddToListOverlay — failures', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.spyOn(console, 'error').mockImplementation(() => {})
    h.fetchMyLists.mockResolvedValue([])
  })

  it("shows the list's own reason when the server gives one", async () => {
    h.addItems.mockRejectedValue(new Error('rate_limited'))

    const w = await pickTheList()

    expect(errors()).toEqual([['portal.lists.errors.rate_limited', 'err']])
    expect(w.find('.atl-row').attributes('disabled')).toBeUndefined()
  })

  it('names the failed action for any other failure, and adds nothing over a rate limit', async () => {
    h.addItems.mockRejectedValueOnce(new Error('http_500'))
    await pickTheList()
    expect(errors()).toEqual([['common.apiError.saveFailed', 'err']])

    h.showToast.mockClear()
    h.addItems.mockRejectedValueOnce(new Error('rate_limited_notified'))
    await pickTheList()
    expect(errors()).toEqual([])
  })

  it('does not report a good add as failed when the refresh after it fails', async () => {
    h.addItems.mockResolvedValue({ success: true })
    h.fetchMyLists.mockRejectedValue(new Error('http_500'))

    await pickTheList()

    expect(h.showToast).toHaveBeenCalledWith('portal.lists.addTo.added', 'ok')
    expect(errors()).toEqual([])
  })

  it('says why a title could not go into the list just created', async () => {
    h.createList.mockResolvedValue({ success: true, id: 2 })
    h.addItems.mockRejectedValue(new Error('owner_muted'))

    await createThenAdd()

    expect(errors()).toEqual([['portal.lists.errors.owner_muted', 'err']])
    expect(h.fetchMyLists).toHaveBeenCalledTimes(1) // the new list still shows up
  })

  it('creates the list once however fast Save is clicked', async () => {
    let finish
    h.createList.mockReturnValue(new Promise(resolve => (finish = resolve)))
    const w = mountOverlay()
    const form = () => w.findComponent({ name: 'ListFormModal' })

    form().vm.$emit('submit', { name: 'New list' })
    form().vm.$emit('submit', { name: 'New list' })
    await flushPromises()

    expect(h.createList).toHaveBeenCalledTimes(1)
    expect(form().props('busy')).toBe(true)
    finish({ success: false })
    await flushPromises()
  })

  it('says the lists could not be loaded when it opens', async () => {
    h.fetchMyLists.mockRejectedValue(new Error('http_500'))
    const w = mountOverlay(false)

    await w.setProps({ open: true })
    await flushPromises()

    expect(errors()).toEqual([['common.apiError.loadFailed', 'err']])
  })
})
