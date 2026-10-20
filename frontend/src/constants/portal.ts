import { REQUEST_STATUS } from '@/constants/requests'

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

/**
 * Person filmography role filter — also the `role` query param used when
 * deep-linking into the person page from detail carousels / cast lists.
 */
export const PERSON_ROLE = Object.freeze({
  ALL: 'all',
  DIRECTOR: 'director',
  ACTING: 'acting',
} as const)

export type PersonRole = (typeof PERSON_ROLE)[keyof typeof PERSON_ROLE]

/**
 * Library availability of a title returned by the portal availability check:
 * a series is `partial` while aired episodes are still missing from Emby.
 */
export const AVAILABILITY = Object.freeze({
  FULL: 'full',
  PARTIAL: 'partial',
} as const)

export type Availability = (typeof AVAILABILITY)[keyof typeof AVAILABILITY]

/**
 * The viewer's playback state of a title (`watch_status` on the items of
 * the profile carousels).
 */
export const WATCH_STATUS = Object.freeze({
  WATCHED: 'watched',
  IN_PROGRESS: 'in_progress',
} as const)

export type WatchStatus = (typeof WATCH_STATUS)[keyof typeof WATCH_STATUS]

/**
 * What a poster's ribbon shows: where the title's request stands, the
 * blacklist marker, or the viewer's playback state.
 */
export const POSTER_STATUS = Object.freeze({
  PENDING: REQUEST_STATUS.PENDING,
  APPROVED: REQUEST_STATUS.APPROVED,
  REJECTED: REQUEST_STATUS.REJECTED,
  BLACKLISTED: 'blacklisted',
  WATCHED: WATCH_STATUS.WATCHED,
  IN_PROGRESS: WATCH_STATUS.IN_PROGRESS,
} as const)

export type PosterStatus = (typeof POSTER_STATUS)[keyof typeof POSTER_STATUS]

/** Ribbon colour (portal token) and label of each poster status. */
export const POSTER_STATUS_RIBBON: Readonly<
  Record<PosterStatus, Readonly<{ color: string; labelKey: string }>>
> = Object.freeze({
  [POSTER_STATUS.PENDING]: {
    color: 'var(--portal-color-warning)',
    labelKey: 'portal.posterCard.statusPending',
  },
  [POSTER_STATUS.APPROVED]: {
    color: 'var(--portal-color-success)',
    labelKey: 'portal.posterCard.statusApproved',
  },
  [POSTER_STATUS.REJECTED]: {
    color: 'var(--portal-color-error)',
    labelKey: 'portal.posterCard.statusRejected',
  },
  [POSTER_STATUS.BLACKLISTED]: {
    color: 'var(--portal-color-neutral-dark)',
    labelKey: 'portal.posterCard.statusBlacklisted',
  },
  [POSTER_STATUS.WATCHED]: {
    color: 'var(--portal-color-premium)',
    labelKey: 'portal.posterCard.statusWatched',
  },
  [POSTER_STATUS.IN_PROGRESS]: {
    color: 'var(--portal-color-info)',
    labelKey: 'portal.posterCard.statusInProgress',
  },
})
