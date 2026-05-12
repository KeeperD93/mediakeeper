/**
 * Portal (user-facing Requests module) routes.
 *
 * Mounted under `/portal` via `PortalLayout.vue`. Every entry must
 * carry `meta.portal: true` so the layout/title logic can branch on it,
 * and `meta.titleKey` so the document title updates on navigation.
 */
export const portalRoutes = [
  {
    path: '',
    name: 'portal-home',
    component: () => import('@/views/portal/PortalHome.vue'),
    meta: { titleKey: 'portal.routeTitles.home', portal: true },
  },
  {
    path: 'requests',
    name: 'portal-requests',
    component: () => import('@/views/portal/PortalDiscover.vue'),
    meta: { titleKey: 'portal.routeTitles.requests', portal: true },
  },
  {
    path: 'leaderboard',
    name: 'portal-leaderboard',
    component: () => import('@/views/portal/PortalLeaderboard.vue'),
    meta: { titleKey: 'portal.routeTitles.leaderboard', portal: true },
  },
  {
    path: 'settings',
    name: 'portal-settings',
    component: () => import('@/views/portal/PortalSettings.vue'),
    meta: { titleKey: 'portal.routeTitles.profile', portal: true },
  },
  {
    path: 'tickets',
    name: 'portal-tickets',
    component: () => import('@/views/portal/PortalTickets.vue'),
    meta: { titleKey: 'portal.routeTitles.tickets', portal: true },
  },
  {
    path: 'changelog',
    name: 'portal-changelog',
    component: () => import('@/views/portal/PortalChangelogView.vue'),
    meta: { titleKey: 'portal.routeTitles.changelog', portal: true },
  },
  {
    path: 'credits',
    name: 'portal-credits',
    component: () => import('@/views/portal/PortalCreditsView.vue'),
    meta: { titleKey: 'portal.routeTitles.credits', portal: true },
  },
  {
    path: 'lists',
    name: 'portal-lists',
    alias: ['lists'],
    component: () => import('@/views/portal/PortalLists.vue'),
    meta: { titleKey: 'portal.routeTitles.lists', portal: true },
  },
  {
    path: 'media/:type/:id',
    name: 'portal-media-detail',
    component: () => import('@/views/portal/PortalMediaDetail.vue'),
    meta: { titleKey: 'portal.routeTitles.media', portal: true },
  },
  {
    path: 'person/:id',
    name: 'portal-person',
    component: () => import('@/views/portal/PortalPerson.vue'),
    meta: { titleKey: 'portal.routeTitles.person', portal: true },
  },
  {
    path: 'collection/:id',
    name: 'portal-collection',
    component: () => import('@/views/portal/PortalCollection.vue'),
    meta: { titleKey: 'portal.routeTitles.collection', portal: true },
  },
  {
    // User profile page — curated recommendations, playback
    // stats, watch history, requests, achievements.
    path: 'me',
    name: 'portal-me',
    component: () => import('@/views/portal/PortalMe.vue'),
    meta: { titleKey: 'portal.routeTitles.me', portal: true },
  },
  {
    // Public profile page — what other users see when they click my
    // name on the leaderboard / nav. The owner can land here too via
    // the "View as others" CTA from /portal/settings.
    path: 'u/:id',
    name: 'portal-user-profile',
    component: () => import('@/views/portal/PortalUserProfile.vue'),
    meta: { titleKey: 'portal.routeTitles.profile', portal: true },
  },
  {
    // Generic browse pages: /portal/category/movies, /series, ...
    path: 'category/:type',
    name: 'portal-category',
    component: () => import('@/views/portal/PortalCategoryPage.vue'),
    meta: { titleKey: 'portal.routeTitles.category', portal: true },
  },
  {
    // Generic browse pages: /portal/platform/netflix, /prime, ...
    path: 'platform/:slug',
    name: 'portal-provider',
    component: () => import('@/views/portal/PortalProviderPage.vue'),
    meta: { titleKey: 'portal.routeTitles.platform', portal: true },
  },
  {
    // Cinema room for an event (3D scene + chat + countdown)
    path: 'rooms/:id',
    name: 'portal-rooms',
    component: () => import('@/views/portal/CinemaRoomView.vue'),
    meta: { titleKey: 'portal.routeTitles.cinemaRoom', portal: true },
  },
  {
    path: 'tickets/:id',
    name: 'portal-ticket-detail',
    component: () => import('@/views/portal/PortalTicketDetail.vue'),
    meta: { titleKey: 'portal.routeTitles.ticketDetail', portal: true },
  },
  {
    path: 'search',
    name: 'portal-search',
    component: () => import('@/views/portal/PortalSearchResults.vue'),
    meta: { titleKey: 'portal.routeTitles.search', portal: true },
  },
  {
    path: 'calendar',
    name: 'portal-calendar',
    component: () => import('@/views/portal/PortalCalendar.vue'),
    meta: { titleKey: 'portal.routeTitles.calendar', portal: true },
  },
  {
    path: 'parties',
    name: 'portal-parties',
    component: () => import('@/views/portal/PortalParties.vue'),
    meta: { titleKey: 'portal.routeTitles.parties', portal: true },
  },
  {
    path: 'wrapped',
    name: 'portal-wrapped',
    component: () => import('@/views/portal/PortalWrapped.vue'),
    meta: { titleKey: 'portal.routeTitles.wrapped', portal: true },
  },
  {
    path: 'maintenance',
    name: 'portal-maintenance',
    component: () => import('@/views/portal/PortalMaintenance.vue'),
    meta: { titleKey: 'pageMeta.maintenanceTitle', portal: true, public: true },
  },
]
