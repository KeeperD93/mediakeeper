import { AVAILABILITY } from '@/constants/portal'
import { REQUEST_STATUS } from '@/constants/requests'

/**
 * Whether the viewer can (re)request a title, given its current request
 * status and library availability: never requested, last request rejected,
 * or served but not fully in Emby (a series still missing aired episodes,
 * whose request modal only offers those, or content gone from Emby).
 */
export function canRequest(status, availability) {
  if (!status || status === REQUEST_STATUS.REJECTED) return true
  return status === REQUEST_STATUS.AVAILABLE && availability !== AVAILABILITY.FULL
}
