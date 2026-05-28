import { describe, it, expect } from 'vitest'
import { reactive, nextTick } from 'vue'
import { useSidebarExpand, hasSubTabs } from '@/composables/useSidebarExpand'

function setup(initialPath = '/') {
  const route = reactive({ path: initialPath })
  const api = useSidebarExpand(route)
  return { route, ...api }
}

describe('hasSubTabs', () => {
  it('is true for modules that expose sub-tabs', () => {
    expect(hasSubTabs('/stats')).toBe(true)
    expect(hasSubTabs('/settings')).toBe(true)
    expect(hasSubTabs('/admin/portal')).toBe(true)
  })

  it('is false for modules without sub-tabs and unknown paths', () => {
    expect(hasSubTabs('/media')).toBe(false)
    expect(hasSubTabs('/')).toBe(false)
    expect(hasSubTabs('/nope')).toBe(false)
  })
})

describe('useSidebarExpand', () => {
  it('opens a module sub-menu without navigating', () => {
    const { route, toggleExpand, isExpanded } = setup('/')
    toggleExpand('/stats')
    expect(isExpanded('/stats')).toBe(true)
    expect(route.path).toBe('/') // stayed on the current page
  })

  it('re-clicking the same module collapses it', () => {
    const { toggleExpand, isExpanded } = setup('/')
    toggleExpand('/stats')
    toggleExpand('/stats')
    expect(isExpanded('/stats')).toBe(false)
  })

  it('opening another module replaces the manual expansion (accordion)', () => {
    const { toggleExpand, isExpanded } = setup('/')
    toggleExpand('/stats')
    toggleExpand('/settings')
    expect(isExpanded('/stats')).toBe(false)
    expect(isExpanded('/settings')).toBe(true)
  })

  it('clears the manual expansion on navigation, route becomes the source of truth', async () => {
    const { route, toggleExpand, isExpanded } = setup('/')
    toggleExpand('/stats')
    route.path = '/settings'
    await nextTick()
    expect(isExpanded('/settings')).toBe(true) // now the active route
    expect(isExpanded('/stats')).toBe(false)
  })

  it('auto-expands the active module from the route alone', () => {
    const { isExpanded } = setup('/stats')
    expect(isExpanded('/stats')).toBe(true)
  })

  it('auto-expands a module when on a nested route', () => {
    const { isExpanded } = setup('/stats/anything')
    expect(isExpanded('/stats')).toBe(true)
  })

  it('requests-admin only auto-expands on an exact match (not its sibling routes)', () => {
    const onUsers = setup('/admin/portal/users')
    expect(onUsers.isExpanded('/admin/portal')).toBe(false)
    const onExact = setup('/admin/portal')
    expect(onExact.isExpanded('/admin/portal')).toBe(true)
  })

  it('never expands a module without sub-tabs, even when toggled', () => {
    const { toggleExpand, isExpanded } = setup('/')
    toggleExpand('/media')
    expect(isExpanded('/media')).toBe(false)
  })

  it('navigating elsewhere collapses a manually-opened module', async () => {
    const { route, toggleExpand, isExpanded } = setup('/')
    toggleExpand('/stats')
    route.path = '/media'
    await nextTick()
    expect(isExpanded('/stats')).toBe(false)
  })
})
