/**
 * Portal "Issues" (tickets): values exchanged with `/api/portal/tickets`.
 */
export const TICKET_STATUS = Object.freeze({
  OPEN: 'open',
  IN_PROGRESS: 'in_progress',
  RESOLVED: 'resolved',
  CLOSED: 'closed',
} as const)

export type TicketStatus = (typeof TICKET_STATUS)[keyof typeof TICKET_STATUS]

/** What a ticket is about, in the order the forms list them. */
export const TICKET_ISSUE_TYPES = Object.freeze([
  'audio',
  'subtitles',
  'video',
  'metadata',
  'playback',
  'file',
  'other',
] as const)

export type TicketIssueType = (typeof TICKET_ISSUE_TYPES)[number]

/** Order of the tickets list. */
export const TICKET_SORT = Object.freeze({
  NEWEST: 'newest',
  OLDEST: 'oldest',
} as const)

export type TicketSort = (typeof TICKET_SORT)[keyof typeof TICKET_SORT]

/**
 * Where the reported media comes from: picked in the Emby library, or typed
 * by hand (sent as `media_type: "other"`).
 */
export const TICKET_SOURCE = Object.freeze({
  LIBRARY: 'library',
  OTHER: 'other',
} as const)

export type TicketSource = (typeof TICKET_SOURCE)[keyof typeof TICKET_SOURCE]
