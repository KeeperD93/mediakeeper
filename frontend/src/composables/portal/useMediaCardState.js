/**
 * Composable used by MediaCard.vue to derive every visual tag / badge /
 * button-label from a single media item prop. Keeps MediaCard.vue under
 * the 300-line file-size cap by pulling the ~120 lines of computed
 * helpers out of the component.
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAvailability } from '@/composables/portal/useAvailability'
import { useRequestStatus } from '@/composables/portal/useRequestStatus'
import { REQUEST_STATUS } from '@/constants/requests'

const NEW_THRESHOLD_DAYS = 7

export function useMediaCardState(props) {
  const { t } = useI18n()
  const { getAvailability } = useAvailability()
  const { getStatus } = useRequestStatus()

  const availData = computed(() => {
    // Items that already carry their own emby_url + availability (e.g. Top20
    // items, which come straight from Emby playback data) bypass the
    // tmdb_id-based lookup and use what the backend handed us directly.
    if (props.item?.emby_url || props.item?.availability) {
      return {
        emby_url: props.item.emby_url || '',
        availability: props.item.availability || 'full',
      }
    }
    const id = props.item?.tmdb_id || props.item?.id
    return id ? getAvailability(id) : null
  })

  const avail = computed(() => availData.value?.availability || null)

  // Global "already requested" status for this tmdb_id. The backend
  // returns null when no active request exists, so the badge / disabled
  // state only show up when reqStatus is truthy.
  //
  // Items served by the profile page carry their own `_request_status`
  // (populated server-side from the user's own requests) — we honour it
  // as a fallback so the button stays disabled even if the global cache
  // wasn't primed for that item (e.g. "Mes demandes" carousel).
  const reqStatus = computed(() => {
    const id = props.item?.tmdb_id || props.item?.id
    const cached = id ? getStatus(id) : null
    if (cached) {
      // The global cache does not track the user's own retry count — only
      // the profile carousel carries it via `_retry_count`. Merge both so
      // the badge stays visible even when the cache is primed.
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

  const postitTooltip = computed(() => {
    const r = reqStatus.value
    if (!r) return ''
    let when = ''
    if (r.requested_at) {
      try { when = new Date(r.requested_at).toLocaleDateString() } catch { /**/ }
    }
    // When the admin has enabled "anonymize_requests", the backend
    // strips `requested_by` from the response for non-admin users — in
    // that case we drop the "by <nickname>" mention entirely and only
    // show the date.
    if (!r.requested_by) {
      return t('portal.card.postit.tooltipAnonymous', { date: when })
    }
    return t('portal.card.postit.tooltip', {
      by: r.requested_by,
      date: when,
    })
  })

  // "New on Emby" ribbon — only items added to the Emby library within
  // the last 7 days. The ``date_created`` field is populated by the
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
  const newRibbonTooltip = computed(() => {
    const raw = props.item?.date_created
    if (!raw) return ''
    try {
      return t('portal.card.newRibbonTooltip', {
        date: new Date(raw).toLocaleDateString(),
      })
    } catch {
      return ''
    }
  })

  // Status dot (availability only)
  // Green dot  = fully available on Emby
  // Orange dot = partially available (some episodes missing)
  // Requested items no longer use a dot — they get a bronze "Requested"
  // tag ribbon instead (see showRequestedTag below).
  const statusDot = computed(() => {
    // Partial must win over the generic "available" branch — a series
    // that's partially on Emby still carries an emby_url (to play what's
    // already there), but the correct visual is the orange dot.
    if (avail.value === 'partial') {
      return { variant: 'partial', tooltip: t('portal.card.partial') }
    }
    if (availData.value?.emby_url || avail.value === 'full') {
      return { variant: 'available', tooltip: t('portal.card.available') }
    }
    return null
  })

  // "Requested" bronze tag — shows when the item has an active request
  // AND is not already available on Emby (available/partial items
  // display their green/orange dot instead).
  const showRequestedTag = computed(() => {
    if (!reqStatus.value) return false
    if (statusDot.value) return false
    // Rejected items use the dedicated red tag instead of the bronze
    // "Requested" ribbon so the user immediately sees the refusal.
    if (isRejected.value) return false
    return true
  })

  const requestStatusLabel = computed(() => {
    const s = props.item?._request_status || reqStatus.value?.status
    if (!s) return ''
    return t(`portal.card.reqStatus.${s}`)
  })

  return {
    availData,
    reqStatus,
    isRejected,
    canResubmit,
    retryCount,
    postitTooltip,
    isNewOnEmby,
    newRibbonTooltip,
    statusDot,
    showRequestedTag,
    requestStatusLabel,
  }
}
