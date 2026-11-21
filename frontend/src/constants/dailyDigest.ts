/** What moved on the viewer's own requests and tickets (`for_you[*].kind` of the digest). */
export const FOR_YOU_KIND = Object.freeze({
  REQUEST_AVAILABLE: 'request_available',
  REQUEST_APPROVED: 'request_approved',
  TICKET_REPLY: 'ticket_reply',
} as const)

export type ForYouKind = (typeof FOR_YOU_KIND)[keyof typeof FOR_YOU_KIND]

/** Types of a news item, as the server validates them. */
export const NEWS_TYPE = Object.freeze({
  ANNOUNCEMENT: 'announcement',
  ADDITIONS: 'additions',
  MAINTENANCE: 'maintenance',
  EVENT: 'event',
  OTHER: 'other',
} as const)

export type NewsType = (typeof NEWS_TYPE)[keyof typeof NEWS_TYPE]

/** Posters an arrow of the "New in the library" rail moves by. */
export const DIGEST_POSTERS_PER_CLICK = 3

/** Sections of a Portal version (`release.categories` of the digest), as the changelog names them. */
export const RELEASE_CATEGORY = Object.freeze({
  ADDED: 'Added',
  CHANGED: 'Changed',
  FIXED: 'Fixed',
  REMOVED: 'Removed',
} as const)

export type ReleaseCategory = (typeof RELEASE_CATEGORY)[keyof typeof RELEASE_CATEGORY]

/** Changes the closed "New version" card lists before « +N other changes ». */
export const DIGEST_RELEASE_TEASER_SIZE = 3
