/**
 * Dashboard widget catalogue — pure data, no Vue runtime hooks.
 *
 * Split out of useDashboardLayout.js to keep file sizes manageable so
 * the composable stays focused on layout state + persistence. Anything
 * exported here is a constant: widget IDs, default grid coordinates,
 * mobile baselines, i18n keys, the layout-version bump counter.
 */
import {
  Calendar,
  CalendarClock,
  CircleCheck,
  CirclePlay,
  ClipboardCheck,
  Clock,
  Copy,
  Database,
  Grid3x3,
  ShieldCheck,
  TrendingUp,
  Users,
  Zap,
} from 'lucide-vue-next'

// Bump when WIDGET_REGISTRY.defaultLayout changes — forces user reset.
export const LAYOUT_VERSION = 22

// Widget badge icons — Lucide components, rendered via <component :is="...">.
export const WIDGET_ICONS = {
  activity: Zap,
  statPlays: CirclePlay,
  statDuration: Clock,
  statDuplicates: Copy,
  statStorage: Database,
  heatmap: Grid3x3,
  topUsers: Users,
  linkWatchlist: ClipboardCheck,
  portalAction: CircleCheck,
  portalEngagement: TrendingUp,
  portalEvents: CalendarClock,
  upcoming: Calendar,
  healthScore: ShieldCheck,
}

export const WIDGET_REGISTRY = {
  activity: { defaultLayout: { x: 0, y: 0, w: 11, h: 30 }, minW: 6, minH: 12 },
  statPlays: { defaultLayout: { x: 21, y: 0, w: 4, h: 5 }, minW: 3, minH: 4 },
  statDuration: { defaultLayout: { x: 25, y: 0, w: 4, h: 5 }, minW: 3, minH: 4 },
  statStorage: { defaultLayout: { x: 29, y: 0, w: 4, h: 5 }, minW: 3, minH: 4 },
  statDuplicates: { defaultLayout: { x: 33, y: 0, w: 3, h: 5 }, minW: 3, minH: 4 },
  topUsers: { defaultLayout: { x: 11, y: 0, w: 10, h: 10 }, minW: 6, minH: 9, maxH: 12 },
  heatmap: { defaultLayout: { x: 28, y: 20, w: 8, h: 10 }, minW: 6, minH: 6 },
  upcoming: { defaultLayout: { x: 0, y: 30, w: 36, h: 15 }, minW: 6, minH: 6 },
  portalAction: { defaultLayout: { x: 11, y: 10, w: 10, h: 8 }, minW: 10, minH: 7 },
  portalEngagement: { defaultLayout: { x: 11, y: 18, w: 10, h: 12 }, minW: 10, minH: 7 },
  portalEvents: { defaultLayout: { x: 28, y: 5, w: 8, h: 15 }, minW: 4, minH: 7 },
  linkWatchlist: { defaultLayout: { x: 21, y: 9, w: 7, h: 4 }, minW: 6, minH: 4 },
  healthScore: { defaultLayout: { x: 21, y: 5, w: 7, h: 4 }, minW: 6, minH: 4 },
}

// Canonical widget IDs — single source of truth so consumers never
// duplicate string literals. Any new widget added to WIDGET_REGISTRY
// above must also appear here so
// consumers (MobileDashboardWidget dispatch, MOBILE_DEFAULT_ORDER…)
// reference the constant instead of duplicating string literals.
export const WIDGET_ID = Object.freeze({
  ACTIVITY: 'activity',
  STAT_PLAYS: 'statPlays',
  STAT_DURATION: 'statDuration',
  STAT_DUPLICATES: 'statDuplicates',
  STAT_STORAGE: 'statStorage',
  TOP_USERS: 'topUsers',
  HEATMAP: 'heatmap',
  UPCOMING: 'upcoming',
  PORTAL_ACTION: 'portalAction',
  PORTAL_ENGAGEMENT: 'portalEngagement',
  PORTAL_EVENTS: 'portalEvents',
  LINK_WATCHLIST: 'linkWatchlist',
  HEALTH_SCORE: 'healthScore',
})

// IDs of the four compact "stat" cards. They render in a fixed 2×2
// grid above the reorderable stack — reordering tiny stat tiles
// individually adds noise without value.
export const MOBILE_STAT_IDS = [
  WIDGET_ID.STAT_PLAYS,
  WIDGET_ID.STAT_DURATION,
  WIDGET_ID.STAT_DUPLICATES,
  WIDGET_ID.STAT_STORAGE,
]

// i18n key per widget for any UI that needs a localised widget label
// (mobile reorder list, desktop edit-bar chip…). Consumers pass these
// keys through $t(). Keeps the i18n contract — no literal label in
// templates. The four stat tiles reuse the same keys their card body
// already renders (dashboard.totalPlays etc.).
export const WIDGET_TITLE_KEY = Object.freeze({
  [WIDGET_ID.ACTIVITY]: 'dashboard.widgetTitles.activity',
  [WIDGET_ID.HEALTH_SCORE]: 'dashboard.widgetTitles.healthScore',
  [WIDGET_ID.PORTAL_ACTION]: 'dashboard.widgetTitles.portalAction',
  [WIDGET_ID.PORTAL_ENGAGEMENT]: 'dashboard.widgetTitles.portalEngagement',
  [WIDGET_ID.PORTAL_EVENTS]: 'dashboard.widgetTitles.portalEvents',
  [WIDGET_ID.UPCOMING]: 'dashboard.widgetTitles.upcoming',
  [WIDGET_ID.TOP_USERS]: 'dashboard.widgetTitles.topUsers',
  [WIDGET_ID.HEATMAP]: 'dashboard.widgetTitles.heatmap',
  [WIDGET_ID.LINK_WATCHLIST]: 'dashboard.widgetTitles.linkWatchlist',
  [WIDGET_ID.STAT_PLAYS]: 'dashboard.totalPlays',
  [WIDGET_ID.STAT_DURATION]: 'dashboard.totalDuration',
  [WIDGET_ID.STAT_DUPLICATES]: 'dashboard.duplicates',
  [WIDGET_ID.STAT_STORAGE]: 'dashboard.storage',
})

// Mobile stack default ordering — the vertical sequence below the
// stats grid, before any user customisation. Mirrors the previously
// hardcoded markup of MobileDashboard.vue so an existing user who has
// never reordered keeps the exact same visual order.
export const MOBILE_DEFAULT_ORDER = [
  WIDGET_ID.HEALTH_SCORE,
  WIDGET_ID.PORTAL_ACTION,
  WIDGET_ID.PORTAL_ENGAGEMENT,
  WIDGET_ID.PORTAL_EVENTS,
  WIDGET_ID.ACTIVITY,
  WIDGET_ID.UPCOMING,
  WIDGET_ID.TOP_USERS,
  WIDGET_ID.HEATMAP,
  WIDGET_ID.LINK_WATCHLIST,
]
