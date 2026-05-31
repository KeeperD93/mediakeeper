/**
 * Cinema room trailer carousel — fetches a queue of trailers and plays
 * each one in full, with a black fade between videos. Drives the
 * preroll screen in CinemaRoomView until the launch countdown starts.
 */
import { ref, computed, onBeforeUnmount, nextTick } from 'vue'
import { useApi } from '@/composables/useApi'

const YT_API_SCRIPT_ID = 'yt-api-script'
const FETCH_INTERVAL_MS = 5 * 60 * 1000
const KEY_PATTERN = /^[a-zA-Z0-9_-]{11}$/

const FADE_IN_MS = 600
const FADE_OUT_MS = 900
const FALLBACK_MS = 2500

function ensureYTApi() {
  return new Promise(resolve => {
    if (window.YT?.Player) {
      resolve()
      return
    }
    if (document.getElementById(YT_API_SCRIPT_ID)) {
      const check = setInterval(() => {
        if (window.YT?.Player) {
          clearInterval(check)
          resolve()
        }
      }, 100)
      return
    }
    const tag = document.createElement('script')
    tag.id = YT_API_SCRIPT_ID
    tag.src = 'https://www.youtube.com/iframe_api'
    document.head.appendChild(tag)
    window.onYouTubeIframeAPIReady = () => resolve()
  })
}

export function useCinemaTrailerCarousel({ playerElRef, initialMuted = true } = {}) {
  const { apiGet } = useApi()

  const queue = ref([])
  const currentIndex = ref(0)
  const videoPlaying = ref(false)
  const transitioning = ref(false)
  const muted = ref(initialMuted)

  const playerId = `yt-cinema-${Date.now()}`
  let player = null
  let refreshTimer = null
  let veilTimer = null
  let fallbackTimer = null

  const currentTrailer = computed(() => queue.value[currentIndex.value] || null)
  const hasTrailer = computed(() => !!currentTrailer.value?.key)
  const fadeStyle = computed(() => ({
    transitionDuration: transitioning.value ? `${FADE_IN_MS}ms` : `${FADE_OUT_MS}ms`,
  }))

  function destroyPlayer() {
    if (player) {
      try {
        player.destroy()
      } catch {
        /* ignore */
      }
      player = null
    }
    // ``YT.Player.destroy()`` releases the internal player state but
    // can leave the actual ``<iframe>`` element behind in the host
    // div, which on some Chromium builds keeps streaming the trailer
    // (audio in particular) in the background. Clear the host so the
    // browser drops the embed entirely.
    const el = playerElRef?.value
    if (el) el.innerHTML = ''
  }

  function createPlayerForCurrent() {
    destroyPlayer()
    const item = currentTrailer.value
    if (!item?.key || !KEY_PATTERN.test(item.key)) return
    if (!window.YT?.Player) return
    const el = playerElRef?.value
    if (!el) return
    // YT.Player replaces the target node, so inject a fresh inner div
    // each time to keep the outer wrapper (which carries the fade
    // overlay and the screen aspect-ratio).
    el.innerHTML = ''
    const target = document.createElement('div')
    target.id = playerId
    el.appendChild(target)
    nextTick(() => {
      player = new window.YT.Player(playerId, {
        host: 'https://www.youtube-nocookie.com',
        videoId: item.key,
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
          onReady: e => {
            if (muted.value) e.target.mute()
            else e.target.unMute()
          },
          onStateChange: e => {
            if (e.data === 1) {
              videoPlaying.value = true
              if (transitioning.value) transitioning.value = false
            }
            if (e.data === 0) advanceNext()
            if (e.data === 2) e.target.playVideo()
          },
          onError: () => advanceNext(),
        },
      })
    })
  }

  function clearVeilTimers() {
    if (veilTimer) {
      clearTimeout(veilTimer)
      veilTimer = null
    }
    if (fallbackTimer) {
      clearTimeout(fallbackTimer)
      fallbackTimer = null
    }
  }

  function advanceNext() {
    if (!queue.value.length) return
    transitioning.value = true
    videoPlaying.value = false
    clearVeilTimers()
    veilTimer = setTimeout(() => {
      currentIndex.value = (currentIndex.value + 1) % queue.value.length
      createPlayerForCurrent()
    }, FADE_IN_MS)
    fallbackTimer = setTimeout(() => {
      if (transitioning.value) transitioning.value = false
    }, FADE_IN_MS + FALLBACK_MS)
  }

  async function fetchQueue() {
    const res = await apiGet('/api/portal/trailers/random?limit=10').catch(() => null)
    if (res?.items?.length) queue.value = res.items
  }

  async function start() {
    await ensureYTApi()
    await fetchQueue()
    if (!queue.value.length) return
    currentIndex.value = 0
    createPlayerForCurrent()
  }

  function applyMute(v) {
    muted.value = !!v
    if (!player) return
    try {
      if (muted.value) player.mute()
      else player.unMute()
    } catch {
      /* ignore */
    }
  }

  refreshTimer = setInterval(() => {
    fetchQueue().catch(() => {})
  }, FETCH_INTERVAL_MS)

  function destroy() {
    if (refreshTimer) {
      clearInterval(refreshTimer)
      refreshTimer = null
    }
    clearVeilTimers()
    destroyPlayer()
  }

  onBeforeUnmount(destroy)

  return {
    queue,
    currentIndex,
    currentTrailer,
    hasTrailer,
    videoPlaying,
    transitioning,
    fadeStyle,
    muted,
    start,
    advanceNext,
    applyMute,
    destroy,
  }
}
