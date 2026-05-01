/**
 * useTrailer
 * ----------
 * Tiny composable that asks the backend for the best available trailer
 * for a given media, using the cascade implemented in
 * ``backend/services/portal/trailers.py``:
 *
 *   1. Emby LocalTrailer  → MP4 streamed via /api/portal/trailers/emby/{id}
 *   2. TMDB videos in user's preferred language
 *   3. TMDB videos in English
 *   4. TMDB videos in the media's original language
 *   5. TMDB videos in any language
 *
 * The backend reads the user's preferred language from their Portal
 * profile, so the caller doesn't have to pass it.
 *
 * Returned shape:
 *   { source: 'emby' | 'youtube' | 'vimeo',
 *     url:    string,           // ready to drop into <video> or <iframe>
 *     key:    string | null,    // provider id when applicable
 *     language: string | null,
 *     name:   string }
 */
import { ref } from 'vue'
import { useApi } from '@/composables/useApi'

// Module-level cache shared across every useTrailer() instance so that
// the hero banner can prefetch the next item's trailer in parallel with
// the current one playing — the rotation then resolves instantly.
const trailerCache = new Map()

function cacheKey(mediaType, tmdbId, embyItemId) {
  return `${mediaType}:${tmdbId}:${embyItemId || ''}`
}

export function useTrailer() {
  const { apiGet } = useApi()
  const trailer = ref(null)
  const loading = ref(false)

  async function fetchFromApi(mediaType, tmdbId, embyItemId) {
    const params = new URLSearchParams({ media_type: mediaType, tmdb_id: String(tmdbId) })
    if (embyItemId) params.set('emby_item_id', embyItemId)
    try {
      const res = await apiGet(`/api/portal/trailers/resolve?${params.toString()}`)
      return res?.trailer || null
    } catch {
      return null
    }
  }

  /**
   * Resolve a trailer for the given media.
   * @param {('movie'|'tv')} mediaType
   * @param {number} tmdbId
   * @param {string=} embyItemId  Optional, enables the Emby LocalTrailers step.
   */
  async function resolve(mediaType, tmdbId, embyItemId = null) {
    if (!mediaType || !tmdbId) {
      trailer.value = null
      return null
    }
    const key = cacheKey(mediaType, tmdbId, embyItemId)
    if (trailerCache.has(key)) {
      trailer.value = trailerCache.get(key)
      return trailer.value
    }
    loading.value = true
    try {
      const result = await fetchFromApi(mediaType, tmdbId, embyItemId)
      trailerCache.set(key, result)
      trailer.value = result
    } finally {
      loading.value = false
    }
    return trailer.value
  }

  /**
   * Fire-and-forget prefetch: resolves the trailer URL and fills the
   * module cache but never touches ``trailer`` so the current playback
   * state stays intact.
   */
  async function prefetch(mediaType, tmdbId, embyItemId = null) {
    if (!mediaType || !tmdbId) return
    const key = cacheKey(mediaType, tmdbId, embyItemId)
    if (trailerCache.has(key)) return
    const result = await fetchFromApi(mediaType, tmdbId, embyItemId)
    trailerCache.set(key, result)
  }

  /**
   * Synchronous cache peek. Returns ``undefined`` when the key has
   * never been resolved, or the cached value (possibly ``null`` when
   * the item is known to have no trailer).
   */
  function peek(mediaType, tmdbId, embyItemId = null) {
    if (!mediaType || !tmdbId) return undefined
    const key = cacheKey(mediaType, tmdbId, embyItemId)
    if (!trailerCache.has(key)) return undefined
    return trailerCache.get(key)
  }

  function clear() {
    trailer.value = null
  }

  return { trailer, loading, resolve, prefetch, peek, clear }
}
