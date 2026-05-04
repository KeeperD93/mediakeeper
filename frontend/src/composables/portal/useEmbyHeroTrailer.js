/**
 * Trailer-player orchestration for EmbyRecentHero — handles YouTube IFrame
 * API loading, Emby <video> playback, mute toggling, and the "trailer ends
 * → next item" auto-advance. Extracted from EmbyRecentHero.vue to keep the
 * component under 300 lines.
 */
import { ref, onBeforeUnmount, nextTick } from 'vue'
import { useTrailer } from '@/composables/portal/useTrailer'
import { useVideoPlayingFlag } from '@/composables/portal/useVideoPlayingFlag'
import { TRAILER_SOURCE } from '@/constants/trailers'

export function useEmbyHeroTrailer({ onTrailerEnded } = {}) {
  const { trailer, resolve: resolveTrailer, peek: peekTrailer, clear: clearTrailer } = useTrailer()
  const muted = ref(true)
  const embyVideoRef = ref(null)
  const videoPlaying = ref(false)
  const playerId = `eh-player-${Date.now()}`
  let player = null

  // Reference-counted body flag (shared with HeroBanner) — drops the
  // topbar's backdrop-filter while a trailer is playing.
  const { setPlaying: setVideoFlag, release: releaseVideoFlag } = useVideoPlayingFlag()

  function setVideoPlaying(v) {
    videoPlaying.value = v
    setVideoFlag(v)
  }

  async function loadTrailer(item) {
    destroyPlayer()
    setVideoPlaying(false)
    clearTrailer()
    if (!item) return
    const type = item.media_type || 'movie'
    const id = item.tmdb_id || item.id
    if (!id) return
    await resolveTrailer(type, id, item.emby_item_id || null)
    if (trailer.value?.source === TRAILER_SOURCE.YOUTUBE && trailer.value?.key) {
      // Wait for Vue to render the <div :id="playerId" /> that the
      // YouTube IFrame API targets. Without this, the DOM element
      // doesn't exist yet when `new YT.Player(playerId, ...)` runs
      // — the player creation fails silently and the user sees the
      // red YouTube play button instead of an autoplaying trailer.
      await nextTick()
      mountYouTubePlayer(trailer.value.key)
    }
  }

  function mountYouTubePlayer(key) {
    if (!window.YT || !window.YT.Player) {
      if (!document.querySelector('script[src*="youtube.com/iframe_api"]')) {
        const tag = document.createElement('script')
        tag.src = 'https://www.youtube.com/iframe_api'
        document.head.appendChild(tag)
      }
      const wait = setInterval(() => {
        if (window.YT && window.YT.Player) {
          clearInterval(wait)
          mountYouTubePlayer(key)
        }
      }, 100)
      return
    }
    destroyPlayer()
    // Safety net: if the user navigated away or the component unmounted
    // between the async resolve and this tick, the target div may no
    // longer exist in the DOM. Bail out gracefully instead of letting
    // the IFrame API throw a cryptic error.
    if (!document.getElementById(playerId)) return
    player = new window.YT.Player(playerId, {
      // Force the iframe origin to ``youtube-nocookie.com`` so the
      // privacy-enhanced mode is honoured even though the IFrame API
      // loader itself is served from ``youtube.com`` (see CSP
      // ``script-src``). Aligns with ``frame-src`` in
      // ``backend/core/security_headers.py``.
      host: 'https://www.youtube-nocookie.com',
      videoId: key,
      playerVars: {
        autoplay: 1,
        controls: 0,
        mute: muted.value ? 1 : 0,
        rel: 0,
        modestbranding: 1,
        playsinline: 1,
        disablekb: 1,
        iv_load_policy: 3,
        // No loop / playlist: with loop=1 + playlist=key, YouTube auto-
        // restarts the same video and the "ended" state (e.data === 0)
        // is never emitted, so onTrailerEnded -> nextItem never fires
        // and the user gets stuck on the same trailer when the sound
        // is on. Letting the video end naturally lets onStateChange
        // forward the event to nextItem and rotate to the next item.
      },
      events: {
        onReady: e => {
          if (muted.value) e.target.mute()
          else e.target.unMute()
          e.target.playVideo()
        },
        onStateChange: e => {
          // 1 = playing, 0 = ended, 2 = paused
          setVideoPlaying(e.data === 1)
          if (e.data === 0) onTrailerEnded?.()
        },
      },
    })
  }

  function destroyPlayer() {
    try {
      if (player && player.destroy) player.destroy()
    } catch {
      /* ignore */
    }
    player = null
    setVideoPlaying(false)
  }

  function toggleMute() {
    muted.value = !muted.value
    if (player) {
      if (muted.value) player.mute()
      else player.unMute()
    }
    if (embyVideoRef.value) {
      embyVideoRef.value.muted = muted.value
    }
  }

  function onEmbyPause() {
    setVideoPlaying(false)
  }
  function onEmbyEnded() {
    setVideoPlaying(false)
    onTrailerEnded?.()
  }

  onBeforeUnmount(() => {
    destroyPlayer()
    clearTrailer()
    releaseVideoFlag()
  })

  return {
    trailer,
    muted,
    embyVideoRef,
    videoPlaying,
    playerId,
    loadTrailer,
    peekTrailer,
    setVideoPlaying,
    destroyPlayer,
    toggleMute,
    onEmbyPause,
    onEmbyEnded,
    clearTrailer,
  }
}
