import { ref, computed, watch } from 'vue'

/**
 * Cinematic black veil between two hero trailers.
 *
 * Drives an asymmetric fade:
 *   1. Fade to black over FADE_IN_MS while the current trailer is still
 *      playing underneath.
 *   2. At full black, the caller swaps the underlying item and loads the
 *      next trailer.
 *   3. When the new trailer actually begins playing (`videoPlaying` ref
 *      flips to true), fade the veil out over FADE_OUT_MS.
 *
 * A safety timer drops the veil after FALLBACK_MS in case the trailer
 * never starts, so the user is never stuck on a black screen.
 *
 * Inputs
 * - videoPlaying : Ref<boolean> — true once the new trailer is rendering frames.
 * - peekItem     : (item) => undefined | null | trailer
 *                  sync cache peek used to skip the cinematic fade when we
 *                  already know the next item has no trailer.
 * - loadItem     : async (item) => void — resolves once the trailer is loaded.
 * - hasTrailer   : () => boolean — read *after* loadItem to decide if the
 *                  veil should be released immediately (no trailer case).
 *
 * Output
 * - transitioning : Ref<boolean>     — bind to `.pt-hero-fade--active`.
 * - fadeStyle     : ComputedRef<obj> — CSS `transition-duration` override.
 * - onItemChange  : (item) => void   — call inside a watcher on the active item.
 * - startInitial  : async (item) => void — call on mount after YT API is ready.
 * - dispose       : () => void       — clear all pending timers on unmount.
 */
export function useHeroCinemaVeil({ videoPlaying, peekItem, loadItem, hasTrailer }) {
  const FADE_IN_MS = 2000
  const FADE_OUT_MS = 3000
  const FALLBACK_MS = 4000

  // Start ON so the backdrop never flashes before the first trailer plays.
  const transitioning = ref(true)

  const fadeStyle = computed(() => ({
    transitionDuration: transitioning.value ? `${FADE_IN_MS}ms` : `${FADE_OUT_MS}ms`,
  }))

  let pendingLoadTimer = null
  let fallbackTimer = null

  function clearPending() {
    if (pendingLoadTimer) {
      clearTimeout(pendingLoadTimer)
      pendingLoadTimer = null
    }
  }
  function clearFallback() {
    if (fallbackTimer) {
      clearTimeout(fallbackTimer)
      fallbackTimer = null
    }
  }

  function onItemChange(item) {
    // Cache-hit shortcut: if we already know the next item has no
    // trailer, skip the full fade and swap straight to the backdrop.
    const cached = peekItem(item)
    if (cached === null) {
      transitioning.value = false
      loadItem(item)
      return
    }
    transitioning.value = true
    clearPending()
    pendingLoadTimer = setTimeout(async () => {
      pendingLoadTimer = null
      try {
        await loadItem(item)
      } catch {
        /* swallow — release the veil below */
      }
      // Uncached miss (prefetch race / API fail) — release veil so the
      // user sees the backdrop instead of waiting for the safety timer.
      if (!hasTrailer()) transitioning.value = false
    }, FADE_IN_MS)
  }

  async function startInitial(item) {
    try {
      await loadItem(item)
    } catch {
      /* swallow — release the veil below */
    }
    if (!hasTrailer()) transitioning.value = false
  }

  // Drop the veil as soon as the new trailer starts rendering frames.
  watch(videoPlaying, v => {
    if (v && transitioning.value) transitioning.value = false
  })

  // Safety net: never hold the user on full black longer than FALLBACK_MS.
  // ``immediate: true`` is critical: the ref starts at ``true`` so without
  // it the watcher never fires on mount and the fallback timer is never
  // armed. When YT silently fails (rate-limit, ad-blocker, network) the
  // PLAYING state event then never comes, the veil stays opaque forever
  // and the backdrop image underneath never shows.
  watch(transitioning, v => {
    if (v) {
      clearFallback()
      fallbackTimer = setTimeout(() => {
        transitioning.value = false
      }, FALLBACK_MS)
    } else {
      clearFallback()
    }
  }, { immediate: true })

  function dispose() {
    clearPending()
    clearFallback()
  }

  return { transitioning, fadeStyle, onItemChange, startInitial, dispose }
}
