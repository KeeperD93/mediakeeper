/**
 * Admin / MediaKeeper backoffice routes.
 *
 * All mounted under the shared `AppLayout` at `/` — the top-level
 * layout wrapper is built in `router/index.js` where these children
 * are plugged in. Keep this file focused on the route declarations so
 * diffs stay surgical when we add/rename backoffice pages.
 */
export const adminRoutes = [
  {
    path: '',
    name: 'dashboard',
    component: () => import('@/views/DashboardView.vue'),
    meta: { titleKey: 'sidebar.dashboard', subtitleKey: 'pageMeta.dashboard' },
  },
  {
    path: 'stats',
    name: 'stats',
    component: () => import('@/views/StatsView.vue'),
    meta: { titleKey: 'stats.title', subtitleKey: 'pageMeta.statistics' },
  },
  {
    path: 'watchlist',
    name: 'watchlist',
    component: () => import('@/views/WatchlistView.vue'),
    meta: { titleKey: 'watchlist.title', subtitleKey: 'pageMeta.watchlist' },
  },
  {
    path: 'media-manager',
    name: 'media-manager',
    component: () => import('@/views/MediaManagerView.vue'),
    meta: { titleKey: 'mediaManager.title', subtitleKey: 'pageMeta.mediaManager' },
  },
  {
    path: 'duplicates',
    name: 'duplicates',
    component: () => import('@/views/DuplicatesView.vue'),
    meta: { titleKey: 'duplicates.title', subtitleKey: 'pageMeta.duplicates' },
  },
  {
    path: 'health',
    name: 'health',
    component: () => import('@/views/HealthCheckView.vue'),
    meta: { titleKey: 'healthCheck.title', subtitleKey: 'pageMeta.health' },
  },
  {
    path: 'subtitles',
    name: 'subtitles',
    component: () => import('@/views/SubtitlesView.vue'),
    meta: { titleKey: 'subtitles.title', subtitleKey: 'pageMeta.subtitles' },
  },
  {
    path: 'notifications',
    name: 'notifications',
    component: () => import('@/views/NotificationsView.vue'),
    meta: { titleKey: 'notifications.title', subtitleKey: 'pageMeta.notifications' },
  },
  {
    path: 'tracker',
    name: 'tracker',
    component: () => import('@/views/PlaceholderView.vue'),
    meta: { titleKey: 'sidebar.tracker', subtitleKey: 'pageMeta.tracker' },
  },
  {
    // Admin side of the Requests module lives under /admin/* so it
    // doesn't collide with the public /portal standalone layout.
    path: 'admin/portal/users',
    name: 'requests-users',
    component: () => import('@/views/RequestsUsersView.vue'),
    meta: { titleKey: 'pageMeta.requestsUsersTitle', subtitleKey: 'pageMeta.requestsUsers' },
  },
  {
    path: 'admin/portal',
    name: 'portal-admin',
    component: () => import('@/views/portal/PortalAdmin.vue'),
    meta: { titleKey: 'pageMeta.requestsAdminTitle', subtitleKey: 'pageMeta.requestsAdmin' },
  },
  {
    path: 'logs',
    name: 'logs',
    component: () => import('@/views/LogsView.vue'),
    meta: { titleKey: 'logs.title', subtitleKey: 'pageMeta.logs' },
  },
  {
    path: 'settings',
    name: 'settings',
    component: () => import('@/views/SettingsView.vue'),
    meta: { titleKey: 'settings.title', subtitleKey: 'pageMeta.settings' },
  },
  {
    path: 'changelog',
    name: 'changelog',
    component: () => import('@/views/ChangelogView.vue'),
    meta: { titleKey: 'changelog.title', subtitleKey: 'pageMeta.changelog' },
  },
]
