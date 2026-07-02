// Feedback (bug/suggestion) form vocabulary. Kept in sync with the backend
// FeedbackReport schema (backend/api/feedback.py) and the tracker taxonomy.

export const FEEDBACK_TYPES = Object.freeze(['bug', 'suggestion'] as const)
export type FeedbackType = (typeof FEEDBACK_TYPES)[number]

// Platform checkboxes; both ticked resolves to the tracker's "both".
export const FEEDBACK_PLATFORMS = Object.freeze(['desktop', 'mobile'] as const)
export type FeedbackPlatform = (typeof FEEDBACK_PLATFORMS)[number]

// Ordered severity → nature. Labels resolve under feedback.tags.<key>.
export const FEEDBACK_TAGS = Object.freeze([
  'urgent',
  'crash',
  'data_loss',
  'security',
  'visual',
  'performance',
  'accessibility',
  'translation',
  'compatibility',
] as const)
export type FeedbackTag = (typeof FEEDBACK_TAGS)[number]

// Discord caps a webhook message at 2000 chars; the live counter keeps the
// whole block (delimiters + labels + meta + fields) under this, mirroring the
// backend guard in services/feedback.py.
export const FEEDBACK_MAX_CHARS = 2000

// Admin backoffice pages → tracker location. `zone`/`module` are the canonical
// taxonomy values sent in the report; `titleKey` localizes the dropdown;
// `tabsPath` links to SIDEBAR_SUB_TABS for the onglet options. Keyed by route
// name so the modal can pre-fill from the page the admin is on.
const ZONE_ADMIN = 'Tableau de bord (admin général)'
const ZONE_PORTAL_ADMIN = 'Admin du Portail'

export interface FeedbackPage {
  route: string
  zone: string
  module: string
  titleKey: string
  tabsPath: string | null
}

export const FEEDBACK_PAGES: readonly FeedbackPage[] = Object.freeze([
  {
    route: 'dashboard',
    zone: ZONE_ADMIN,
    module: 'Dashboard',
    titleKey: 'sidebar.dashboard',
    tabsPath: null,
  },
  {
    route: 'stats',
    zone: ZONE_ADMIN,
    module: 'Statistiques',
    titleKey: 'stats.title',
    tabsPath: '/stats',
  },
  {
    route: 'watchlist',
    zone: ZONE_ADMIN,
    module: 'Vigilance media (Watchlist)',
    titleKey: 'watchlist.title',
    tabsPath: '/watchlist',
  },
  {
    route: 'media-manager',
    zone: ZONE_ADMIN,
    module: 'Gestionnaire media',
    titleKey: 'mediaManager.title',
    tabsPath: null,
  },
  {
    route: 'duplicates',
    zone: ZONE_ADMIN,
    module: 'Doublons',
    titleKey: 'duplicates.title',
    tabsPath: '/duplicates',
  },
  {
    route: 'health',
    zone: ZONE_ADMIN,
    module: 'Santé (Healthcheck)',
    titleKey: 'healthCheck.title',
    tabsPath: '/health',
  },
  {
    route: 'subtitles',
    zone: ZONE_ADMIN,
    module: 'Sous-titres',
    titleKey: 'subtitles.title',
    tabsPath: '/subtitles',
  },
  {
    route: 'notifications',
    zone: ZONE_ADMIN,
    module: 'Notifications Discord',
    titleKey: 'notifications.title',
    tabsPath: '/notifications',
  },
  { route: 'logs', zone: ZONE_ADMIN, module: 'Logs', titleKey: 'logs.title', tabsPath: '/logs' },
  {
    route: 'settings',
    zone: ZONE_ADMIN,
    module: 'Paramètres admin',
    titleKey: 'settings.title',
    tabsPath: '/settings',
  },
  {
    route: 'changelog',
    zone: ZONE_ADMIN,
    module: 'Changelog admin',
    titleKey: 'changelog.title',
    tabsPath: null,
  },
  {
    route: 'about',
    zone: ZONE_ADMIN,
    module: 'À propos / Attribution',
    titleKey: 'attribution.about.title',
    tabsPath: null,
  },
  {
    route: 'tracker',
    zone: ZONE_ADMIN,
    module: 'Tracker',
    titleKey: 'sidebar.tracker',
    tabsPath: null,
  },
  {
    route: 'requests-users',
    zone: ZONE_PORTAL_ADMIN,
    module: 'Gestion utilisateurs portail',
    titleKey: 'pageMeta.requestsUsersTitle',
    tabsPath: null,
  },
  {
    route: 'portal-admin',
    zone: ZONE_PORTAL_ADMIN,
    module: 'Espace admin Portail',
    titleKey: 'pageMeta.requestsAdminTitle',
    tabsPath: '/admin/portal',
  },
])
