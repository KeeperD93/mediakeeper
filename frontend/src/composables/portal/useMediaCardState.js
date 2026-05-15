/**
 * State derived from a single portal media item, consumed by MediaCard
 * (now a thin wrapper around PosterCard). Returns only the bits the
 * wrapper still needs to drive PosterCard props — the old visual tags
 * (statusDot, requestedTag, requestStatusLabel) are now handled inside
 * PosterCard via the unified status ribbon.
 */
import { computed } from 'vue'
import { useAvailability } from '@/composables/portal/useAvailability'
import { useRequestStatus } from '@/composables/portal/useRequestStatus'
import { REQUEST_STATUS } from '@/constants/requests'

const NEW_THRESHOLD_DAYS = 7

export function useMediaCardState(props) {
  const { getAvailability } = useAvailability()
  const { getStatus } = useRequestStatus()

  const availData = computed(() => {
    // Single source of truth: always consult the canonical availability
    // cache when a tmdb_id is known. The backend `/availability` endpoint
    // computes partial-vs-full for series properly, so a series that's
    // missing episodes correctly resolves to 'partial' even when the row
    // payload (e.g. /top20) pre-stamped 'full' as a hint.
    const id = props.item?.tmdb_id || props.item?.id
    const cached = id ? getAvailability(id) : null
    if (cached) return cached
    // Fallback: items that carry an inline `emby_url` / `availability`
    // (Top20, hero strips) render their pre-stamped value until the
    // availability cache is primed.
    if (props.item?.emby_url || props.item?.availability) {
      return {
        emby_url: props.item.emby_url || '',
        availability: props.item.availability || 'full',
      }
    }
    return null
  })

  // Global "already requested" status for this tmdb_id. The backend
  // returns null when no active request exists. Items served by the
  // profile page may carry their own `_request_status` — honour it as a
  // fallback so the badge stays visible even if the global cache wasn't
  // primed for that item.
  const reqStatus = computed(() => {
    const id = props.item?.tmdb_id || props.item?.id
    const cached = id ? getStatus(id) : null
    if (cached) {
      const rc = props.item?._retry_count
      if (rc && !cached.retry_count) return { ...cached, retry_count: rc }
      return cached
    }
    const rs = props.item?._request_status
    if (rs) {
      return {
        status: rs,
        requested_at: null,
        requested_by: null,
        request_id: null,
        retry_count: props.item?._retry_count || 0,
        reject_reason: props.item?._reject_reason || null,
      }
    }
    return null
  })

  const isRejected = computed(() => reqStatus.value?.status === REQUEST_STATUS.REJECTED)
  const canResubmit = computed(() => isRejected.value)
  const retryCount = computed(() => reqStatus.value?.retry_count || 0)

  // "New on Emby" ribbon — only items added to the Emby library within
  // the last 7 days. The `date_created` field is populated by the
  // backend /available/* endpoints; TMDB-only items never carry it, so
  // the ribbon stays hidden by default.
  const isNewOnEmby = computed(() => {
    const raw = props.item?.date_created
    if (!raw) return false
    const added = new Date(raw)
    if (Number.isNaN(added.getTime())) return false
    const ageDays = (Date.now() - added.getTime()) / (1000 * 60 * 60 * 24)
    return ageDays >= 0 && ageDays < NEW_THRESHOLD_DAYS
  })

  // Effective request status — prefers the explicit `_request_status`
  // stamped by the profile carousel, falls back to the global cache.
  // Used by the wrapper to detect a blacklist marker.
  const displayedReqStatus = computed(
    () => props.item?._request_status || reqStatus.value?.status || null,
  )

  return {
    availData,
    reqStatus,
    isRejected,
    canResubmit,
    retryCount,
    isNewOnEmby,
    displayedReqStatus,
  }
}
