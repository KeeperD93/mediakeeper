/**
 * The sidebar notice renders only when a newer release exists, opens the
 * release page in a new tab, and falls back to an icon with an accessible
 * label when the sidebar is collapsed.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { ref } from 'vue'

const status = ref(null)
const load = vi.fn()
vi.mock('@/composables/useUpdateCheck', () => ({ useUpdateCheck: () => ({ status, load }) }))
vi.mock('vue-i18n', () => ({
  useI18n: () => ({ t: (key, params) => (params ? `${key}:${params.version}` : key) }),
}))

import SidebarUpdateNotice from '@/components/layout/SidebarUpdateNotice.vue'

const UPDATE = {
  update_available: true,
  latest_version: '1.0.1',
  release_url: 'https://github.com/KeeperD93/mediakeeper/releases/tag/v1.0.1',
}

describe('SidebarUpdateNotice', () => {
  beforeEach(() => {
    status.value = null
    load.mockClear()
  })

  it('loads the status on mount and stays hidden without an update', () => {
    status.value = { update_available: false, latest_version: null, release_url: null }
    const w = mount(SidebarUpdateNotice)
    expect(load).toHaveBeenCalledTimes(1)
    expect(w.find('a').exists()).toBe(false)
  })

  it('links to the release notes in a new tab', () => {
    status.value = UPDATE
    const link = mount(SidebarUpdateNotice).get('a')
    expect(link.attributes('href')).toBe(UPDATE.release_url)
    expect(link.attributes('target')).toBe('_blank')
    expect(link.attributes('rel')).toBe('noopener noreferrer')
    expect(link.text()).toBe('sidebar.updateAvailable:1.0.1')
  })

  it('shows only the icon with an accessible label when collapsed', () => {
    status.value = UPDATE
    const link = mount(SidebarUpdateNotice, { props: { collapsed: true } }).get('a')
    expect(link.text()).toBe('')
    expect(link.attributes('aria-label')).toBe('sidebar.updateAvailableTitle:1.0.1')
  })

  it('renders nothing when the release URL is unsafe', () => {
    status.value = { ...UPDATE, release_url: 'javascript:alert(1)' }
    expect(mount(SidebarUpdateNotice).find('a').exists()).toBe(false)
  })
})
