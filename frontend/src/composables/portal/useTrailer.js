/**
 * useTrailer
 * ----------
 * Tiny composable that asks the backend for the available trailers for a
 * given media, using the cascade implemented in
 * ``backend/services/portal/trailers.py``:
 *
 *   1. Emby LocalTrailer  → MP4 streamed via /api/portal/trailers/emby/{id}
 *   2. TMDB videos in user's preferred language
 *   3. TMDB videos in English
 *   4. TMDB videos in the media's original language
 *   5. TMDB videos in any language
 *
 * The backend resolves the viewer's active locale from the request
 * (the X-MK-Locale header), so the caller doesn't have to pass it.
 *
 * Exposes both ``trailer`` (the best descriptor — drives the button
 * visibility) and ``candidates`` (the full ranked list, best first) so the
 * player can fall back to another one when the first is region-blocked by
 * the provider. Each descriptor:
 *   { source: 'emby' | 'youtube' | 'vimeo',
 *     url:    string,           // ready to drop into <video> or <iframe>
 *     key:    string | null,    // provider id when applicable
 *     language: string | null,
 *     name:   string }
 */
import { ref } from 'vue'
import { useApi } from '@/composables/useApi'

// Module-level cache shared across every useTrailer() instance: key -> the
// ranked candidate list (best first). The hero can prefetch the next item's
// trailers in parallel with the current one playing — the rotation then
// resolves instantly.
const trailerCache = new Map()

function cacheKey(mediaType, tmdbId, embyItemId) {
  return `${mediaType}:${tmdbId}:${embyItemId || ''}`
}

export function useTrailer() {
  const { apiGet } = useApi()
  const trailer = ref(null)
  const candidates = ref([])
  const loading = ref(false)

  async function fetchFromApi(mediaType, tmdbId, embyItemId) {
    const params = new URLSearchParams({ media_type: mediaType, tmdb_id: String(tmdbId) })
    if (embyItemId) params.set('emby_item_id', embyItemId)
    try {
      const res = await apiGet(`/api/portal/trailers/resolve?${params.toString()}`)
      // Tolerate the legacy single-trailer response shape too.
      return res?.candidates || (res?.trailer ? [res.trailer] : [])
    } catch {
      return []
    }
  }

  function applyList(list) {
    candidates.value = list
    trailer.value = list[0] || null
  }

  /**
   * Resolve trailers for the given media.
   * @param {('movie'|'tv')} mediaType
   * @param {number} tmdbId
   * @param {string=} embyItemId  Optional, enables the Emby LocalTrailers step.
   */
  async function resolve(mediaType, tmdbId, embyItemId = null) {
    if (!mediaType || !tmdbId) {
      applyList([])
      return null
    }
    const key = cacheKey(mediaType, tmdbId, embyItemId)
    if (trailerCache.has(key)) {
      applyList(trailerCache.get(key))
      return trailer.value
    }
    loading.value = true
    try {
      const list = await fetchFromApi(mediaType, tmdbId, embyItemId)
      trailerCache.set(key, list)
      applyList(list)
    } finally {
      loading.value = false
    }
    return trailer.value
  }

  /**
   * Fire-and-forget prefetch: fills the module cache but never touches the
   * reactive refs, so the current playback state stays intact.
   */
  async function prefetch(mediaType, tmdbId, embyItemId = null) {
    if (!mediaType || !tmdbId) return
    const key = cacheKey(mediaType, tmdbId, embyItemId)
    if (trailerCache.has(key)) return
    trailerCache.set(key, await fetchFromApi(mediaType, tmdbId, embyItemId))
  }

  function clear() {
    applyList([])
  }

  return { trailer, candidates, loading, resolve, prefetch, clear }
}
