import { ref, watch } from 'vue'
import { SIDEBAR_SUB_TABS } from '@/constants/sidebarSubTabs'

/**
 * True when a module route exposes sidebar sub-tabs.
 */
export function hasSubTabs(path) {
  return Array.isArray(SIDEBAR_SUB_TABS[path]) && SIDEBAR_SUB_TABS[path].length > 0
}

/**
 * Sidebar module sub-tab expansion state.
 *
 * Clicking a module that has sub-tabs opens its panel without navigating, so
 * the user can browse the sub-tabs while staying on the current page. The
 * manual expansion is cleared on every navigation, leaving the active route as
 * the single source of truth — the module the user is actually on stays open on
 * its own.
 *
 * @param {{ path: string }} route - reactive route object from vue-router `useRoute()`.
 */
export function useSidebarExpand(route) {
  const expandedModule = ref(null)

  function toggleExpand(path) {
    expandedModule.value = expandedModule.value === path ? null : path
  }

  watch(
    () => route.path,
    () => {
      expandedModule.value = null
    },
  )

  function isExpanded(path) {
    if (!hasSubTabs(path)) return false
    if (expandedModule.value === path) return true
    // The requests-admin module shares its prefix with sibling routes
    // (/admin/portal/users), so it only auto-expands on an exact match.
    if (path === '/admin/portal') return route.path === path
    return route.path === path || route.path.startsWith(path + '/')
  }

  return { expandedModule, toggleExpand, isExpanded }
}
