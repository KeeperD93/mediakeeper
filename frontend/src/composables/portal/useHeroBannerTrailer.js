/**
 * Trailer-player orchestration for HeroBanner — YouTube IFrame API
 * bootstrap, Emby <video> playback, force-resume-on-pause, mute control
 * and the "trailer ended → rotate" signal. Extracted from HeroBanner.vue
 * to keep the component under 300 lines.
 *
 * Differs from useEmbyHeroTrailer in three specifics:
 *   - pausing the trailer is NOT allowed (auto-resumes),
 *   - an onEnded callback is surfaced so the parent can rotate hero items,
 *   - the YouTube id is validated before handing it to YT.Player.
 */
import { ref, onUnmounted, nextTick } from 'vue'
import { useTrailer } from '@/composables/portal/useTrailer'
import { useVideoPlayingFlag } from '@/composables/portal/useVideoPlayingFlag'
import { TRAILER_SOURCE } from '@/constants/trailers'

export function useHeroBannerTrailer({ onEnded } = {}) {
  const {
    trailer,
    resolve: resolveTrailer,
    prefetch: prefetchTrailer,
    peek: peekTrailer,
    clear: clearTrailer,
  } = useTrailer()
  const muted = ref(true)
  const videoPlaying = ref(false)
  const embyVideoRef = ref(null)
  const playerId = `yt-hero-${Date.now()}`
  let player = null

  const { setPlaying: setVideoFlag, release: releaseVideoFlag } = useVideoPlayingFlag()
  function setVideoPlaying(v) {
    videoPlaying.value = v
    setVideoFlag(v)
  }

  function destroyPlayer() {
    if (player) {
      try { player.destroy() } catch { /* ignore */ }
      player = null
    }
  }

  function createPlayer(videoId) {
    destroyPlayer()
    if (!window.YT?.Player) return
    nextTick(() => {
      player = new window.YT.Player(playerId, {
        // Pin the iframe origin to ``youtube-nocookie.com`` so the
        // privacy-enhanced mode applies even though the IFrame API
        // loader itself ships from ``youtube.com`` (see CSP
        // ``script-src`` and ``frame-src`` in
        // ``backend/core/security_headers.py``).
        host: 'https://www.youtube-nocookie.com',
        videoId,
        playerVars: {
          autoplay: 1,
          mute: muted.value ? 1 : 0,
          controls: 0,
          showinfo: 0,
          rel: 0,
          modestbranding: 1,
          iv_load_policy: 3,
          disablekb: 1,
          fs: 0,
          playsinline: 1,
        },
        events: {
          onReady: (e) => {
            if (muted.value) e.target.mute()
            else e.target.unMute()
          },
          onStateChange: (e) => {
            // 1 = playing, 0 = ended, 2 = paused
            setVideoPlaying(e.data === 1)
            if (e.data === 0) onEnded?.()
            // Force resume if paused by any means — the hero trailer
            // is a background decoration, not a manual playback.
            if (e.data === 2) e.target.playVideo()
          },
          onError: () => {
            // Video unavailable / removed / blocked — keep backdrop.
            setVideoPlaying(false)
            clearTrailer()
            destroyPlayer()
          },
        },
      })
    })
  }

  async function loadTrailer(item) {
    clearTrailer()
    setVideoPlaying(false)
    destroyPlayer()
    if (!item?.tmdb_id && !item?.id) return
    const id = item.tmdb_id || item.id
    const type = item.media_type || 'movie'
    await resolveTrailer(type, id, item.emby_item_id || null)
    if (!trailer.value) return
    if (trailer.value.source === TRAILER_SOURCE.YOUTUBE && trailer.value.key) {
      if (!/^[a-zA-Z0-9_-]{11}$/.test(trailer.value.key)) return
      await nextTick()
      createPlayer(trailer.value.key)
    }
    // Emby and Vimeo render via the template — nothing to do here.
  }

  // Lazy-load the YouTube IFrame API once.
  function ensureYTApi() {
    return new Promise((resolve) => {
      if (window.YT?.Player) { resolve(); return }
      if (document.getElementById('yt-api-script')) {
        const check = setInterval(() => {
          if (window.YT?.Player) { clearInterval(check); resolve() }
        }, 100)
        return
      }
      const tag = document.createElement('script')
      tag.id = 'yt-api-script'
      tag.src = 'https://www.youtube.com/iframe_api'
      document.head.appendChild(tag)
      window.onYouTubeIframeAPIReady = () => resolve()
    })
  }

  function toggleMute() {
    muted.value = !muted.value
    if (player) {
      if (muted.value) player.mute()
      else player.unMute()
    }
    // Native <video> reacts to the bound :muted prop automatically.
  }

  function setMuted(v) {
    muted.value = v
    if (player) {
      if (v) player.mute()
      else player.unMute()
    }
  }

  function onEmbyPause() {
    const v = embyVideoRef.value
    // Block manual pause from keyboard / picture-in-picture.
    if (v && !v.ended) {
      v.play().catch(() => { /* autoplay policy may reject; harmless */ })
    }
  }
  function onEmbyEnded() {
    setVideoPlaying(false)
    onEnded?.()
  }

  onUnmounted(() => {
    destroyPlayer()
    releaseVideoFlag()
  })

  return {
    trailer,
    muted,
    videoPlaying,
    embyVideoRef,
    playerId,
    loadTrailer,
    prefetchTrailer,
    peekTrailer,
    ensureYTApi,
    toggleMute,
    setMuted,
    onEmbyPause,
    onEmbyEnded,
    clearTrailer,
    setVideoPlaying,
  }
}
