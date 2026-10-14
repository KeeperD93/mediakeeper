import { AVAILABILITY } from '@/constants/portal'
import { REQUEST_STATUS } from '@/constants/requests'

/**
 * Whether the viewer can (re)request a title, given its current request
 * status and library availability: never requested, last request rejected,
 * or a served series that still misses aired episodes (the request modal
 * then only offers the missing ones).
 */
export function canRequest(status, availability) {
  if (!status || status === REQUEST_STATUS.REJECTED) return true
  return status === REQUEST_STATUS.AVAILABLE && availability === AVAILABILITY.PARTIAL
}
