/**
 * Sidebar sub-tabs configuration.
 *
 * Each module that previously rendered an in-page TabStrip exposes its
 * tabs here so the AppSidebar can mount them as sub-entries under the
 * parent module link. The selected tab is carried in the URL via
 * `?tab=<id>`; views read `route.query.tab` and stay in sync.
 *
 * Keep this list aligned with each view's TAB_COMPONENTS / activeTab
 * mapping — it is the single source of truth for which tabs the
 * navigation surfaces.
 */
import { markRaw } from 'vue'
import {
  LayoutGrid,
  Users,
  Clock,
  BarChart3,
  Wrench,
  AlertTriangle,
  Eye,
  Calendar,
  Ban,
  Copy,
  Settings,
  FileText,
  Search,
  History,
  Bell,
  FileEdit,
  Moon,
  ShieldCheck,
  Sliders,
  Palette,
  Archive,
  TestTube,
  Shield,
  Newspaper,
  Star,
  Sparkles,
  Slash,
  Bug,
} from 'lucide-vue-next'

export const SIDEBAR_SUB_TABS = {
  '/stats': [
    { id: 'general', labelKey: 'stats.general', icon: markRaw(LayoutGrid) },
    { id: 'users', labelKey: 'stats.users', icon: markRaw(Users) },
    { id: 'activity', labelKey: 'stats.activity', icon: markRaw(Clock) },
    { id: 'charts', labelKey: 'stats.charts', icon: markRaw(BarChart3) },
    { id: 'tools', labelKey: 'stats.tools', icon: markRaw(Wrench) },
  ],
  '/watchlist': [
    { id: 'missing', labelKey: 'watchlist.missing', icon: markRaw(AlertTriangle) },
    { id: 'timeline', labelKey: 'watchlist.timeline', icon: markRaw(Clock) },
    { id: 'suivi', labelKey: 'watchlist.tracked', icon: markRaw(Eye) },
    { id: 'calendar', labelKey: 'watchlist.calendar', icon: markRaw(Calendar) },
    { id: 'ignored', labelKey: 'watchlist.ignored', icon: markRaw(Ban) },
  ],
  '/duplicates': [
    { id: 'duplicates', labelKey: 'duplicates.title', icon: markRaw(Copy) },
    { id: 'ignored', labelKey: 'duplicates.ignoredTab', icon: markRaw(Ban) },
    { id: 'history', labelKey: 'duplicates.historyTab', icon: markRaw(Clock) },
    { id: 'rules', labelKey: 'duplicates.rulesTab', icon: markRaw(Settings) },
  ],
  '/health': [
    { id: 'health', labelKey: 'healthCheck.tabs.health', icon: markRaw(ShieldCheck) },
    { id: 'config', labelKey: 'healthCheck.tabs.config', icon: markRaw(Settings) },
  ],
  '/subtitles': [
    { id: 'library', labelKey: 'subtitles.library', icon: markRaw(Calendar) },
    { id: 'search', labelKey: 'subtitles.search', icon: markRaw(Search) },
    { id: 'history', labelKey: 'subtitles.historyTab', icon: markRaw(History) },
    { id: 'statistics', labelKey: 'subtitles.statistics', icon: markRaw(BarChart3) },
  ],
  '/notifications': [
    { id: 'agents', labelKey: 'notifications.tabs.agents', icon: markRaw(Bell) },
    { id: 'templates', labelKey: 'notifications.tabs.templates', icon: markRaw(FileEdit) },
    { id: 'rules', labelKey: 'notifications.tabs.rules', icon: markRaw(Moon) },
    { id: 'history', labelKey: 'notifications.tabs.history', icon: markRaw(History) },
    { id: 'config', labelKey: 'notifications.tabs.config', icon: markRaw(Settings) },
  ],
  '/logs': [
    { id: 'logs', labelKey: 'logs.tabLogs', icon: markRaw(FileText) },
    { id: 'config', labelKey: 'logs.tabConfig', icon: markRaw(Settings) },
  ],
  '/settings': [
    { id: 'general', labelKey: 'settings.tabGeneral', icon: markRaw(Sliders) },
    { id: 'appearance', labelKey: 'settings.tabAppearance', icon: markRaw(Palette) },
    { id: 'config', labelKey: 'settings.tabConfig', icon: markRaw(Settings) },
    { id: 'scheduler', labelKey: 'settings.tabScheduler', icon: markRaw(Clock) },
    { id: 'backup', labelKey: 'settings.tabBackup', icon: markRaw(Archive) },
    { id: 'test', labelKey: 'settings.tabTest', icon: markRaw(TestTube) },
    { id: 'security', labelKey: 'settings.tabSecurity', icon: markRaw(Shield) },
  ],
  '/admin/portal': [
    { id: 'blacklist', labelKey: 'portal.admin.tabs.blacklist', icon: markRaw(Slash) },
    { id: 'news', labelKey: 'portal.admin.tabs.news', icon: markRaw(Newspaper) },
    { id: 'featured', labelKey: 'portal.admin.tabs.featured', icon: markRaw(Star) },
    { id: 'xpEvents', labelKey: 'portal.admin.tabs.xpEvents', icon: markRaw(Sparkles) },
    { id: 'settings', labelKey: 'portal.admin.tabs.settings', icon: markRaw(Settings) },
    { id: 'debug', labelKey: 'portal.admin.tabs.debug', icon: markRaw(Bug) },
  ],
}

/**
 * Returns the configured sub-tabs for a given module route, or null.
 * Matches both the exact path and any nested path (e.g. `/stats/anything`).
 */
export function getSubTabs(routePath) {
  if (!routePath) return null
  for (const parent of Object.keys(SIDEBAR_SUB_TABS)) {
    if (routePath === parent || routePath.startsWith(parent + '/')) {
      return { parent, tabs: SIDEBAR_SUB_TABS[parent] }
    }
  }
  return null
}
