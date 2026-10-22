import { SIDEBAR_SUB_TABS } from '@/constants/sidebarSubTabs'
import { FEEDBACK_PAGES } from '@/constants/feedback'

/**
 * Report location (page + tab) of an admin page. Without a known `?tab=` the
 * page shows its first tab (useTabSync), so that tab is picked as well.
 */
export function locationFromRoute(routeName, tab) {
  const page = FEEDBACK_PAGES.find(p => p.route === routeName)
  if (!page) return { pageRoute: '', tabId: '' }
  const tabs = page.tabsPath ? SIDEBAR_SUB_TABS[page.tabsPath] || [] : []
  return { pageRoute: page.route, tabId: (tabs.find(tb => tb.id === tab) ?? tabs[0])?.id ?? '' }
}
