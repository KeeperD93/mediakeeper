/**
 * Lifecycle statuses for portal media requests.
 *
 * `ACTIONABLE_REQUEST_STATUSES` lists the subset that admins can still act
 * on (approve / reject). Used by admin filters and notification badges.
 */
export const REQUEST_STATUS = Object.freeze({
  PENDING: 'pending',
  APPROVED: 'approved',
  REJECTED: 'rejected',
} as const)

export type RequestStatus = (typeof REQUEST_STATUS)[keyof typeof REQUEST_STATUS]

export const ACTIONABLE_REQUEST_STATUSES: readonly RequestStatus[] = [REQUEST_STATUS.PENDING]

/**
 * Max unique tmdb_ids the backend accepts per batch-status call (mirrors
 * `BATCH_STATUS_MAX_IDS` in backend/api/portal/requests.py). The frontend
 * chunks larger lists to stay under it instead of triggering a 422.
 */
export const BATCH_STATUS_MAX_IDS = 100

/**
 * Page-size options for the admin requests queue (server-side pagination).
 * Values stay within the `per_page` bound (1–100) enforced by
 * `/api/portal/requests/admin`.
 */
export const REQUEST_PAGE_SIZES = Object.freeze([10, 25, 50, 100] as const)

export const DEFAULT_REQUEST_PAGE_SIZE = 25

/**
 * Sort keys for the admin requests queue. Sent to the backend, which maps
 * them to a SQL `ORDER BY` — keep in sync with `_REQUEST_SORTS` in
 * backend/services/portal/requests.py.
 */
export const REQUEST_SORT = Object.freeze({
  RECENT: 'recent',
  OLDEST: 'oldest',
  TITLE: 'title',
} as const)

export type RequestSort = (typeof REQUEST_SORT)[keyof typeof REQUEST_SORT]
