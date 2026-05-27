import { reactive } from 'vue'
import { useApi } from '@/composables/useApi'

// Global cache: tmdb_id -> { availability, emby_item_id, emby_url, _ts }
//
// A 60 s TTL lets newly-added Emby content show up quickly after an admin
// approve → scan → import cycle without forcing users to hard-refresh. The
// backend endpoint is cheap (single Emby index lookup) so the extra round
// trip is acceptable.
const cache = reactive({})
const CACHE_TTL_MS = 60_000

function _isFresh(entry) {
  if (!entry || typeof entry !== 'object') return false
  const ts = entry._ts
  return typeof ts === 'number' && Date.now() - ts < CACHE_TTL_MS
}

// Module-scoped coalescing queue. The Portal home fires ~13 carousel
// loaders in parallel; each one used to POST /availability independently
// the moment its data arrived, swamping the endpoint and stacking 429
// toasts. We now batch every checkAvailability() call landing inside the
// same microtask tick into a single POST with the deduped union of items.
let pendingItems = []
let pendingResolvers = []
let flushScheduled = false

// useApi() returns plain refs + a closure around fetchApiResponse — safe
// to invoke at module scope, but we lazy-init so unit tests that mock
// the module can intercept it cleanly.
let _apiPost = null
function _getApiPost() {
  if (!_apiPost) _apiPost = useApi().apiPost
  return _apiPost
}

async function _flushQueue() {
  const items = pendingItems
  const resolvers = pendingResolvers
  pendingItems = []
  pendingResolvers = []
  flushScheduled = false

  // Dedupe across all coalesced callers — two carousels both asking
  // for the same tmdb_id only count once in the POST payload.
  const seen = new Set()
  const unique = []
  for (const it of items) {
    const k = String(it.tmdb_id)
    if (seen.has(k)) continue
    seen.add(k)
    unique.push(it)
  }
  if (!unique.length) {
    resolvers.forEach(r => r())
    return
  }

  try {
    const apiPost = _getApiPost()
    const res = await apiPost('/api/portal/availability', { items: unique })
    const now = Date.now()
    if (res?.results) {
      for (const [key, val] of Object.entries(res.results)) {
        // A payload with every Emby field null means the backend has no
        // match for that tmdb_id (legacy shape, kept for forward-compat
        // with older API revisions that return `{availability:null,...}`
        // instead of bare `null`). Treat it as an empty stamp so
        // MediaCard can fall back to the inline hint baked into
        // /library/recent while EmbyTmdbIndex catches up.
        const hasMatch = val && (val.availability || val.emby_item_id || val.emby_url)
        cache[key] = hasMatch ? { ...val, _ts: now } : { _ts: now, _empty: true }
      }
    }
    // Stamp missing ids so the TTL applies to "not available" too.
    for (const item of unique) {
      const key = String(item.tmdb_id)
      if (!(key in cache)) {
        cache[key] = { _ts: now, _empty: true }
      }
    }
  } catch {
    // Silently fail — cards just won't show dots
  } finally {
    resolvers.forEach(r => r())
  }
}

export function useAvailability() {
  /**
   * Check availability for a list of items.
   * Each item must have tmdb_id (or id) and media_type.
   * Fresh cache hits are skipped; stale / missing entries are queued
   * for the next microtask flush so concurrent callers share one POST.
   */
  async function checkAvailability(items) {
    if (!items?.length) return

    const toCheck = []
    const seen = new Set()
    for (const it of items) {
      const id = it.tmdb_id || it.id
      if (!id || seen.has(id)) continue
      const key = String(id)
      if (_isFresh(cache[key])) continue
      seen.add(id)
      toCheck.push({ tmdb_id: id, media_type: it.media_type || 'movie' })
    }

    if (!toCheck.length) return

    return new Promise(resolve => {
      pendingItems.push(...toCheck)
      pendingResolvers.push(resolve)
      if (!flushScheduled) {
        flushScheduled = true
        queueMicrotask(_flushQueue)
      }
    })
  }

  /**
   * Get availability for a single tmdb_id.
   * Returns { availability: 'full'|'partial'|null, emby_item_id, emby_url }
   * or null when the cached entry is empty or stale.
   */
  function getAvailability(tmdbId) {
    const entry = cache[String(tmdbId)]
    if (!entry || entry._empty) return null
    if (!_isFresh(entry)) return null
    return entry
  }

  /**
   * Drop a single item from the cache so the next ``checkAvailability``
   * refetches it. Use after an admin approves a request and an Emby
   * scan has likely updated availability.
   */
  function invalidate(tmdbId) {
    if (!tmdbId) return
    delete cache[String(tmdbId)]
  }

  function clearCache() {
    for (const k of Object.keys(cache)) delete cache[k]
  }

  return { checkAvailability, getAvailability, invalidate, clearCache, cache }
}
