/**
 * Trailer-player orchestration for HeroBanner — YouTube IFrame API
 * bootstrap, Emby <video> playback, force-resume-on-pause, mute control
 * and the "trailer ended → rotate" signal. Extracted from HeroBanner.vue
 * to keep the component under 300 lines.
 *
 * The EmbyRecentHero on the home page used to share a sibling composable
 * (useEmbyHeroTrailer); that hero now ships without any trailer player
 * — backdrop slideshow only — so this is currently the only trailer
 * orchestrator in the portal.
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
  // Generation counter so a stale resolution that finishes AFTER a
  // newer loadTrailer was issued doesn't mount its own player on top
  // of the fresh one. Without it, two concurrent loads (parent
  // changing props.item while the first await is still in flight)
  // race to createPlayer and the user sees two trailers chain-loading.
  let loadGeneration = 0

  const { setPlaying: setVideoFlag, release: releaseVideoFlag } = useVideoPlayingFlag()
  function setVideoPlaying(v) {
    videoPlaying.value = v
    setVideoFlag(v)
  }

  // Tracks whether the current player has reached the playing state
  // at least once. Used to ignore the legitimate initial buffering
  // (state 3 before state 1) while tearing the iframe down for any
  // mid-playback regression. Reset by destroyPlayer.
  let everPlayed = false
  // Watchdog that defers ``setVideoPlaying(true)`` until the trailer
  // has genuinely advanced past frame 0. YouTube fires state-1 (playing)
  // before the autoplay request has actually started rendering frames
  // — during that gap the centre play/pause glyph is still painted on
  // top, and revealing the iframe at full opacity makes it visible to
  // the user for a few seconds. Polling currentTime gives us a reliable
  // "really playing" signal. Capped at 2 s so we never sit on an
  // invisible iframe forever if YouTube silently fails.
  let playWatchdog = null
  function clearPlayWatchdog() {
    if (playWatchdog) {
      clearInterval(playWatchdog)
      playWatchdog = null
    }
  }

  function destroyPlayer() {
    if (player) {
      try {
        player.destroy()
      } catch {
        /* ignore */
      }
      player = null
    }
    clearPlayWatchdog()
    everPlayed = false
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
          // Always boot the player muted so the browser autoplay policy
          // can never refuse the playback request. If we let an unmuted
          // first frame through, YouTube freezes on its own centred
          // pause indicator and the iframe never recovers because the
          // overlay sits under ``pointer-events: none``. The real
          // ``muted`` state is applied immediately in ``onReady`` below.
          mute: 1,
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
          onReady: e => {
            if (muted.value) e.target.mute()
            else e.target.unMute()
          },
          onStateChange: e => {
            // 1 = playing, 0 = ended, 2 = paused, 3 = buffering,
            // 5 = cued, -1 = unstarted.
            if (e.data === 1) {
              // YouTube announces "playing" before the very first
              // frame of OUR trailer is on screen. Two warm-up cases
              // routinely surface the centre play/pause glyph during
              // that window: the autoplay handshake (state 1 fires
              // before paint) and a pre-roll ad (state 1 fires
              // against the ad's own video_id, not ours).
              // Defer setVideoPlaying(true) until both:
              //   1. currentTime is past frame 0
              //   2. the video_id reported by the player matches our
              //      requested trailer key (= the real trailer, not
              //      a pre-roll ad).
              // Falls back after 8 s so we never sit on an invisible
              // iframe forever if YouTube silently fails.
              if (playWatchdog || videoPlaying.value) return
              const expectedKey = trailer.value?.key || ''
              let attempts = 0
              playWatchdog = setInterval(() => {
                attempts += 1
                let t = 0
                let vid = ''
                try {
                  t = player?.getCurrentTime?.() || 0
                  vid = player?.getVideoData?.()?.video_id || ''
                } catch {
                  /* keep defaults */
                }
                const realPlaying = t > 0.1 && (!expectedKey || vid === expectedKey)
                if (realPlaying) {
                  clearPlayWatchdog()
                  setVideoPlaying(true)
                  everPlayed = true
                } else if (attempts > 80) {
                  clearPlayWatchdog()
                  setVideoPlaying(true)
                  everPlayed = true
                }
              }, 100)
              return
            }
            setVideoPlaying(false)
            if (e.data === 0) {
              onEnded?.()
              return
            }
            // Initial buffering / cued states are normal before the
            // first playback — let them play out. After the first
            // successful play, any non-playing state would surface
            // YouTube's centre play/pause glyph or spinner, so tear
            // the iframe down to keep the backdrop clean. The next
            // rotation mounts a fresh player for the next item.
            if (everPlayed) {
              clearTrailer()
              destroyPlayer()
            }
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
    const token = ++loadGeneration
    clearTrailer()
    setVideoPlaying(false)
    destroyPlayer()
    if (!item?.tmdb_id && !item?.id) return
    const id = item.tmdb_id || item.id
    const type = item.media_type || 'movie'
    await resolveTrailer(type, id, item.emby_item_id || null)
    // Bail out silently if a newer load was issued while we were
    // awaiting the resolve — its own token now owns the player slot.
    if (token !== loadGeneration) return
    if (!trailer.value) return
    if (trailer.value.source === TRAILER_SOURCE.YOUTUBE && trailer.value.key) {
      if (!/^[a-zA-Z0-9_-]{11}$/.test(trailer.value.key)) return
      await nextTick()
      if (token !== loadGeneration) return
      createPlayer(trailer.value.key)
    }
    // Emby and Vimeo render via the template — nothing to do here.
  }

  // Lazy-load the YouTube IFrame API once.
  function ensureYTApi() {
    return new Promise(resolve => {
      if (window.YT?.Player) {
        resolve()
        return
      }
      // Safety net: if the IFrame API script is blocked (ad-blocker,
      // network, rate-limit), resolve anyway after 5 s so the caller
      // proceeds. ``createPlayer`` silently bails out without YT, the
      // rest of the hero (backdrop, title, rotation, fallback veil)
      // keeps working.
      const giveUp = setTimeout(resolve, 5000)
      const finish = () => {
        clearTimeout(giveUp)
        resolve()
      }
      if (document.getElementById('yt-api-script')) {
        const check = setInterval(() => {
          if (window.YT?.Player) {
            clearInterval(check)
            finish()
          }
        }, 100)
        return
      }
      const tag = document.createElement('script')
      tag.id = 'yt-api-script'
      tag.src = 'https://www.youtube.com/iframe_api'
      document.head.appendChild(tag)
      window.onYouTubeIframeAPIReady = () => finish()
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
      v.play().catch(() => {
        /* autoplay policy may reject; harmless */
      })
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
    destroyPlayer,
  }
}
