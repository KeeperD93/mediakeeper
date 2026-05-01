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
