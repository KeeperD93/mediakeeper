import { reactive } from 'vue'
import { useApi } from '@/composables/useApi'
import { BATCH_STATUS_MAX_IDS, REQUEST_STATUS } from '@/constants/requests'

// Global cache: tmdb_id -> { status, requested_at, requested_by, request_id, _ts }
// Mirrors useAvailability so MediaCard can simply lookup both caches
// without firing per-card requests.
//
// Why a TTL: an admin can toggle the `anonymize_requests` flag at any
// moment. The backend strips `requested_by` from future responses, but
// connected users would keep seeing the old cached entries (that still
// include the username) until their next hard refresh. A short TTL
// ensures the cache auto-refreshes within ~30s without requiring an
// explicit page reload.
const cache = reactive({})
const CACHE_TTL_MS = 30_000

function _isFresh(entry) {
  if (!entry || typeof entry !== 'object') return false
  const ts = entry._ts
  if (typeof ts !== 'number') return false
  return Date.now() - ts < CACHE_TTL_MS
}

export function useRequestStatus() {
  const { apiPost } = useApi()

  /**
   * Batch lookup of request status for a list of items. Items already
   * in the cache AND still fresh (younger than CACHE_TTL_MS) are
   * skipped. Results are merged into the global cache so all MediaCards
   * refresh reactively.
   *
   * The backend only returns active statuses (pending / approved /
   * available) — rejected items are deliberately omitted so the user
   * can re-request them, and missing entries simply mean "not requested".
   */
  async function checkStatus(items) {
    if (!items?.length) return

    const toCheck = []
    const seen = new Set()
    for (const it of items) {
      const raw = it.tmdb_id ?? it.id
      if (raw == null) continue
      // Coerce at boundary: backend expects strict list[int]. A stray string
      // id (e.g. from a TMDB credits payload) used to trigger a silent 422
      // that wiped the entire batch — now we drop only the malformed entry.
      const id = Number(raw)
      if (!Number.isInteger(id) || seen.has(id)) continue
      const key = String(id)
      // Only skip IDs whose cache entry is still fresh. Stale or
      // missing entries get re-queried so the admin's latest
      // anonymize_requests toggle takes effect without a hard reload.
      if (key in cache && _isFresh(cache[key])) continue
      seen.add(id)
      toCheck.push(id)
    }
    if (!toCheck.length) return

    // The backend rejects more than BATCH_STATUS_MAX_IDS unique ids per call
    // (422 too_many_tmdb_ids). Large views (multi-carousel home, infinite
    // scroll, cold cache) blow past it, so split into capped chunks run in
    // parallel — allSettled keeps a transient failure on one chunk from
    // wiping the badges the others resolved.
    const now = Date.now()
    const chunks = []
    for (let i = 0; i < toCheck.length; i += BATCH_STATUS_MAX_IDS) {
      chunks.push(toCheck.slice(i, i + BATCH_STATUS_MAX_IDS))
    }
    const settled = await Promise.allSettled(
      chunks.map(ids => apiPost('/api/portal/requests/batch-status', { tmdb_ids: ids })),
    )
    settled.forEach((outcome, i) => {
      if (outcome.status !== 'fulfilled') return // chunk failed → retry next call
      const res = outcome.value
      if (res?.results) {
        for (const [key, val] of Object.entries(res.results)) {
          cache[key] = val ? { ...val, _ts: now } : null
        }
      }
      // Stamp this chunk's misses (no active request) so they aren't
      // re-queried until the TTL lapses — same shape as populated entries.
      for (const id of chunks[i]) {
        const key = String(id)
        if (!(key in cache) || cache[key] === null) {
          cache[key] = { _ts: now, _empty: true }
        }
      }
    })
  }

  /**
   * Lookup the cached status for a single tmdb_id. Returns null if
   * not yet checked, if the cached entry is stale, or if the item has
   * never been requested. Returns an object { status, requested_at,
   * requested_by?, request_id } for items with an active request.
   *
   * ``requested_by`` is optional: when the admin has enabled
   * ``anonymize_requests``, the backend strips it from the response.
   */
  function getStatus(tmdbId) {
    if (!tmdbId) return null
    const entry = cache[String(tmdbId)]
    if (!entry || entry._empty) return null
    if (!_isFresh(entry)) return null
    return entry
  }

  /**
   * Manually mark an item as requested right after a successful
   * RequestModal submit, so the UI updates without waiting for the
   * next batch refresh.
   */
  function markRequested(tmdbId, payload = {}) {
    if (!tmdbId) return
    cache[String(tmdbId)] = {
      status: REQUEST_STATUS.PENDING,
      requested_at: new Date().toISOString(),
      requested_by: payload.requested_by || 'you',
      request_id: payload.request_id || null,
      retry_count: payload.retry_count || 0,
      _ts: Date.now(),
    }
  }

  /**
   * Patch the cached status for an item after an admin mutation
   * (approve / reject / mark available). For ``rejected``, the entry
   * is kept with ``status: 'rejected'`` — MediaCard uses that to
   * surface the "Rejected" sash + "Re-request" CTA instead of the
   * neutral "Request" default that a cleared cache would show.
   */
  function markStatus(tmdbId, newStatus, extra = {}) {
    if (!tmdbId) return
    const key = String(tmdbId)
    const prev = cache[key] || {}
    cache[key] = {
      ...prev,
      ...extra,
      status: newStatus,
      _ts: Date.now(),
      _empty: false,
    }
  }

  /**
   * Drop a single item from the cache so the next ``checkStatus`` call
   * refetches it from the backend. Useful after operations whose exact
   * final state is non-trivial (batch updates, server-side cascades…).
   */
  function invalidate(tmdbId) {
    if (!tmdbId) return
    delete cache[String(tmdbId)]
  }

  /**
   * Nuke the cache entirely. Called when the Portal home page
   * mounts/activates so each visit starts from a clean slate — that's
   * the main safety net for the "admin just toggled anonymize_requests"
   * scenario: navigating back to Home forces a full re-fetch.
   */
  function clearCache() {
    for (const k of Object.keys(cache)) {
      delete cache[k]
    }
  }

  return {
    checkStatus,
    getStatus,
    markRequested,
    markStatus,
    invalidate,
    clearCache,
    cache,
  }
}
