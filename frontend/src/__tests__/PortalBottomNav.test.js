import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'

vi.mock('lucide-vue-next', () => ({
  Home: { name: 'HomeStub', template: '<i data-icon="home" />' },
  User: { name: 'UserStub', template: '<i data-icon="user" />' },
  Compass: { name: 'CompassStub', template: '<i data-icon="compass" />' },
  LifeBuoy: { name: 'LifeBuoyStub', template: '<i data-icon="lifebuoy" />' },
  Library: { name: 'LibraryStub', template: '<i data-icon="library" />' },
}))

import PortalBottomNav from '@/components/portal/PortalBottomNav.vue'
import { PORTAL_TAB } from '@/constants/portal'

function render(props = {}) {
  return mount(PortalBottomNav, { props })
}

function tabNames(wrapper) {
  return wrapper.findAll('.pt-bottom-tab').map(b => b.attributes('aria-label'))
}

describe('PortalBottomNav', () => {
  it('renders Home, Profile, Lists, Tickets for a viewer without admin requests', () => {
    const w = render({ showRequestsTab: false })
    expect(tabNames(w)).toEqual([
      'portal.tabs.home',
      'portal.tabs.profile',
      'portal.lists.navLabel',
      'portal.tabs.problems',
    ])
  })

  it('inserts Requests after Lists when showRequestsTab is true', () => {
    const w = render({ showRequestsTab: true })
    expect(tabNames(w)).toEqual([
      'portal.tabs.home',
      'portal.tabs.profile',
      'portal.lists.navLabel',
      'portal.tabs.discover',
      'portal.tabs.problems',
    ])
  })

  it('hides Requests when showRequestsTab is false', () => {
    const w = render({ showRequestsTab: false })
    expect(tabNames(w)).not.toContain('portal.tabs.discover')
  })

  it('emits navigate with PORTAL_TAB.LISTS when Lists is clicked', async () => {
    const w = render({ showRequestsTab: true })
    const listsButton = w
      .findAll('.pt-bottom-tab')
      .find(b => b.attributes('aria-label') === 'portal.lists.navLabel')
    await listsButton.trigger('click')
    const events = w.emitted('navigate')
    expect(events).toBeTruthy()
    expect(events[0]).toEqual([PORTAL_TAB.LISTS])
  })

  it('marks only Lists with aria-current="page" when activeTab is LISTS', () => {
    const w = render({ showRequestsTab: true, activeTab: PORTAL_TAB.LISTS })
    const current = w
      .findAll('.pt-bottom-tab')
      .filter(b => b.attributes('aria-current') === 'page')
    expect(current).toHaveLength(1)
    expect(current[0].attributes('aria-label')).toBe('portal.lists.navLabel')
  })

  it('keeps Tickets active when activeTab is TICKET_DETAIL', () => {
    const w = render({ showRequestsTab: true, activeTab: PORTAL_TAB.TICKET_DETAIL })
    const current = w
      .findAll('.pt-bottom-tab')
      .filter(b => b.attributes('aria-current') === 'page')
    expect(current).toHaveLength(1)
    expect(current[0].attributes('aria-label')).toBe('portal.tabs.problems')
  })
})
