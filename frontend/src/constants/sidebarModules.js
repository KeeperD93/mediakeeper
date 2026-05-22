/**
 * Top-level sidebar navigation modules.
 * Consumed by AppSidebar.vue. Counter values and isMobile filtering
 * stay in the component because they are reactive runtime values.
 *
 * `badgeKey` resolves against `useSidebarCounters().counters` at render
 * time; `desktopOnly` hides the item on mobile viewports.
 */
export const SIDEBAR_MODULES = Object.freeze([
  Object.freeze({ to: '/stats', icon: 'stats', labelKey: 'sidebar.statistics' }),
  Object.freeze({
    to: '/watchlist',
    icon: 'watchlist',
    labelKey: 'sidebar.watchlist',
    badgeKey: 'watchlistMissing',
    badgeColor: 'red',
  }),
  Object.freeze({
    to: '/media-manager',
    icon: 'media',
    labelKey: 'sidebar.mediaManager',
    desktopOnly: true,
  }),
  Object.freeze({
    to: '/duplicates',
    icon: 'duplicates',
    labelKey: 'sidebar.duplicates',
    badgeKey: 'duplicates',
    badgeColor: 'red',
  }),
  Object.freeze({ to: '/health', icon: 'healthcheck', labelKey: 'sidebar.healthCheck' }),
  Object.freeze({ to: '/subtitles', icon: 'subtitles', labelKey: 'sidebar.subtitles' }),
  Object.freeze({ to: '/notifications', icon: 'notifications', labelKey: 'sidebar.notifications' }),
  Object.freeze({ to: '/tracker', icon: 'tracker', labelKey: 'sidebar.tracker' }),
])
