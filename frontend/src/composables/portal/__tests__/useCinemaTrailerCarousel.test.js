/**
 * Cinema room trailer carousel — composable behavior.
 *
 * Mocks the YT IFrame API + apiGet so we can assert:
 *   1. initial fetch populates the queue;
 *   2. ENDED state-change advances the index to the next trailer;
 *   3. queue loops back to 0 once the last item ended.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ref, nextTick } from 'vue'

const apiGetMock = vi.fn()
vi.mock('@/composables/useApi', () => ({
  useApi: () => ({ apiGet: apiGetMock }),
}))

let lastPlayer = null
let onStateChangeHandler = null
let playerCalls = 0

function installYTStub() {
  lastPlayer = null
  onStateChangeHandler = null
  playerCalls = 0
  function FakePlayer(targetId, opts) {
    playerCalls += 1
    onStateChangeHandler = opts.events.onStateChange
    this.targetId = targetId
    this.videoId = opts.videoId
    this.destroy = vi.fn()
    this.mute = vi.fn()
    this.unMute = vi.fn()
    this.playVideo = vi.fn()
    lastPlayer = this
    opts.events.onReady?.({ target: this })
  }
  window.YT = {
    Player: FakePlayer,
    PlayerState: { ENDED: 0, PLAYING: 1, PAUSED: 2 },
  }
}

function buildItem(key, title = 'A title') {
  return {
    key,
    title,
    source: 'youtube',
    emby_item_id: `emby-${key}`,
    tmdb_id: 1234,
    media_type: 'movie',
    emby_url: `https://emby.example/web/index.html#!/item?id=emby-${key}`,
  }
}

const VALID_KEYS = ['aaaaaaaaaaa', 'bbbbbbbbbbb', 'ccccccccccc']

describe('useCinemaTrailerCarousel', () => {
  beforeEach(() => {
    apiGetMock.mockReset()
    installYTStub()
    document.body.innerHTML = ''
  })

  it('populates the queue from /api/portal/trailers/random and starts the first trailer', async () => {
    apiGetMock.mockResolvedValue({ items: VALID_KEYS.map(buildItem) })

    const playerEl = ref(document.createElement('div'))
    document.body.appendChild(playerEl.value)

    const { useCinemaTrailerCarousel } =
      await import('@/composables/portal/useCinemaTrailerCarousel')
    const carousel = useCinemaTrailerCarousel({ playerElRef: playerEl })

    await carousel.start()
    await nextTick()

    expect(apiGetMock).toHaveBeenCalledWith('/api/portal/trailers/random?limit=10')
    expect(carousel.queue.value).toHaveLength(3)
    expect(carousel.currentIndex.value).toBe(0)
    expect(carousel.currentTrailer.value.key).toBe('aaaaaaaaaaa')
    expect(playerCalls).toBe(1)
    expect(lastPlayer.videoId).toBe('aaaaaaaaaaa')

    carousel.destroy()
  })

  it('advances the index on YT ENDED state-change and loops back to 0 at the end', async () => {
    apiGetMock.mockResolvedValue({ items: VALID_KEYS.map(buildItem) })

    const playerEl = ref(document.createElement('div'))
    document.body.appendChild(playerEl.value)

    const { useCinemaTrailerCarousel } =
      await import('@/composables/portal/useCinemaTrailerCarousel')
    const carousel = useCinemaTrailerCarousel({ playerElRef: playerEl })

    await carousel.start()
    await nextTick()

    expect(carousel.currentIndex.value).toBe(0)

    // First trailer ends → advanceNext schedules a setTimeout(FADE_IN_MS).
    vi.useFakeTimers()
    onStateChangeHandler({ data: 0, target: lastPlayer })
    expect(carousel.transitioning.value).toBe(true)
    vi.advanceTimersByTime(700)
    await nextTick()
    expect(carousel.currentIndex.value).toBe(1)

    onStateChangeHandler({ data: 0, target: lastPlayer })
    vi.advanceTimersByTime(700)
    await nextTick()
    expect(carousel.currentIndex.value).toBe(2)

    // Loop: third ENDED rolls back to index 0.
    onStateChangeHandler({ data: 0, target: lastPlayer })
    vi.advanceTimersByTime(700)
    await nextTick()
    expect(carousel.currentIndex.value).toBe(0)

    vi.useRealTimers()
    carousel.destroy()
  })

  it('applyMute(true) calls player.mute() and applyMute(false) calls unMute()', async () => {
    apiGetMock.mockResolvedValue({ items: [buildItem('aaaaaaaaaaa')] })
    const playerEl = ref(document.createElement('div'))
    document.body.appendChild(playerEl.value)

    const { useCinemaTrailerCarousel } =
      await import('@/composables/portal/useCinemaTrailerCarousel')
    const carousel = useCinemaTrailerCarousel({ playerElRef: playerEl, initialMuted: true })
    await carousel.start()
    await nextTick()

    carousel.applyMute(false)
    expect(lastPlayer.unMute).toHaveBeenCalledTimes(1)
    carousel.applyMute(true)
    expect(lastPlayer.mute).toHaveBeenCalled()

    carousel.destroy()
  })

  it('handles an empty trailers response without throwing', async () => {
    apiGetMock.mockResolvedValue({ items: [] })
    const playerEl = ref(document.createElement('div'))

    const { useCinemaTrailerCarousel } =
      await import('@/composables/portal/useCinemaTrailerCarousel')
    const carousel = useCinemaTrailerCarousel({ playerElRef: playerEl })
    await carousel.start()

    expect(carousel.queue.value).toHaveLength(0)
    expect(carousel.hasTrailer.value).toBe(false)
    expect(playerCalls).toBe(0)

    carousel.destroy()
  })
})
