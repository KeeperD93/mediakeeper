/**
 * PortalLists.vue — admin tab gating + double-render regression guard.
 *
 * The page now exposes a 3rd tab (`admin`) only when the viewer's
 * profile role is `admin`. When that tab is active the page must mount
 * the AdminListsTab sub-component AND skip the standard list-row /
 * empty-state block (otherwise both views would render at once).
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'

const profileRef = ref({ role: 'user' })
const listsRef = ref([])
const publicListsRef = ref([])

vi.mock('vue-i18n', () => ({
  useI18n: () => ({
    t: (key, params) => (params ? `${key}:${JSON.stringify(params)}` : key),
  }),
}))

vi.mock('@/composables/portal/usePortalAuth', () => ({
  usePortalAuth: () => ({ profile: profileRef }),
}))

vi.mock('@/composables/portal/usePortalLists', () => ({
  usePortalLists: () => ({
    lists: listsRef,
    publicLists: publicListsRef,
    fetchMyLists: vi.fn(() => Promise.resolve(listsRef.value)),
    fetchPublicLists: vi.fn(() => Promise.resolve(publicListsRef.value)),
    fetchList: vi.fn(),
    createList: vi.fn(),
    updateList: vi.fn(),
    deleteList: vi.fn(),
    copyList: vi.fn(),
    removeItems: vi.fn(),
    removeContributor: vi.fn(),
    adminUndelete: vi.fn(),
    adminHardDelete: vi.fn(),
    adminMuteOwner: vi.fn(),
    exportUrl: vi.fn(() => '#'),
  }),
}))

vi.mock('@/composables/useToast', () => ({
  useToast: () => ({ showToast: vi.fn() }),
}))

vi.mock('@/composables/useConfirm', () => ({
  useConfirm: () => vi.fn(() => Promise.resolve(true)),
}))

vi.mock('@/components/portal/lists/AdminListsTab.vue', () => ({
  default: {
    name: 'AdminListsTab',
    template: '<div class="adm-lists-stub" />',
  },
}))

vi.mock('@/components/portal/lists/ListFormModal.vue', () => ({
  default: { name: 'ListFormModal', template: '<div />' },
}))

vi.mock('@/components/portal/lists/ListRow.vue', () => ({
  default: {
    name: 'ListRow',
    props: ['lst'],
    template: '<div class="list-row-stub" />',
  },
}))

vi.mock('@/components/portal/lists/ListExpansion.vue', () => ({
  default: { name: 'ListExpansion', template: '<div />' },
}))

vi.mock('@/components/common/TabStrip.vue', () => ({
  default: {
    name: 'TabStrip',
    props: ['modelValue', 'tabs'],
    emits: ['update:modelValue'],
    template:
      '<div class="tab-strip-stub" :data-tab-ids="tabs.map(t => t.id).join(\',\')" />',
  },
}))

vi.mock('@/components/common/MkSpinner.vue', () => ({
  default: { name: 'MkSpinner', template: '<div class="spinner-stub" />' },
}))

vi.mock('@/assets/styles/portal/admin-rich-row-header.css', () => ({}))
vi.mock('@/assets/styles/portal/admin-rich-row.css', () => ({}))
vi.mock('@/assets/styles/portal/admin-rich-row-actions.css', () => ({}))

import PortalLists from '@/views/portal/PortalLists.vue'

async function mountPage({ role = 'user', initialTab = 'mine' } = {}) {
  profileRef.value = { role }
  const wrapper = mount(PortalLists)
  await flushPromises()
  if (initialTab !== 'mine') {
    // simulate user clicking another tab via the TabStrip emit
    wrapper.vm.activeTab = initialTab
    await flushPromises()
  }
  return wrapper
}

describe('PortalLists.vue — admin tab', () => {
  beforeEach(() => {
    profileRef.value = { role: 'user' }
    listsRef.value = []
    publicListsRef.value = []
  })

  it('does NOT expose the admin tab to non-admin viewers', async () => {
    const wrapper = await mountPage({ role: 'user' })
    const strip = wrapper.find('.tab-strip-stub')
    expect(strip.attributes('data-tab-ids')).toBe('mine,public')
  })

  it('exposes the admin tab to admin viewers', async () => {
    const wrapper = await mountPage({ role: 'admin' })
    const strip = wrapper.find('.tab-strip-stub')
    expect(strip.attributes('data-tab-ids')).toBe('mine,public,admin')
  })

  it('mounts AdminListsTab when activeTab=admin and viewer is admin', async () => {
    const wrapper = await mountPage({ role: 'admin', initialTab: 'admin' })
    expect(wrapper.find('.adm-lists-stub').exists()).toBe(true)
  })

  it('does NOT render the list-row / empty-state block on the admin tab', async () => {
    const wrapper = await mountPage({ role: 'admin', initialTab: 'admin' })
    expect(wrapper.find('.arr-list').exists()).toBe(false)
    expect(wrapper.find('.arr-empty').exists()).toBe(false)
  })
})
