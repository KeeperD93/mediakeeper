/**
 * Portal tab / route-name identifiers. Must stay in sync with the
 * `name:` fields declared in `router/index.js` for the `/portal/*`
 * children — the nav components (PortalNav, PortalBottomNav,
 * usePortalNav) compare against these strings to highlight the active
 * tab.
 */
export const PORTAL_TAB = Object.freeze({
  HOME: 'portal-home',
  ME: 'portal-me',
  TICKETS: 'portal-tickets',
  TICKET_DETAIL: 'portal-ticket-detail',
  REQUESTS: 'portal-requests',
  LISTS: 'portal-lists',
} as const)

export type PortalTab = (typeof PORTAL_TAB)[keyof typeof PORTAL_TAB]
