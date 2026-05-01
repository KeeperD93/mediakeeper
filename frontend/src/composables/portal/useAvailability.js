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
  return typeof ts === 'number' && (Date.now() - ts) < CACHE_TTL_MS
}

export function useAvailability() {
  const { apiPost } = useApi()

  /**
   * Check availability for a list of items.
   * Each item must have tmdb_id (or id) and media_type.
   * Fresh cache hits are skipped; stale / missing entries are re-fetched.
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

    try {
      const res = await apiPost('/api/portal/availability', { items: toCheck })
      const now = Date.now()
      if (res?.results) {
        for (const [key, val] of Object.entries(res.results)) {
          cache[key] = val ? { ...val, _ts: now } : { _ts: now, _empty: true }
        }
      }
      // Stamp missing ids so the TTL applies to "not available" too.
      for (const item of toCheck) {
        const key = String(item.tmdb_id)
        if (!(key in cache)) {
          cache[key] = { _ts: now, _empty: true }
        }
      }
    } catch {
      // Silently fail — cards just won't show dots
    }
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
