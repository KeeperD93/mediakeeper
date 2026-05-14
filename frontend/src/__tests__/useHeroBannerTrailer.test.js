import { describe, it, expect, vi, beforeEach } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { nextTick } from 'vue'

const resolveTrailer = vi.fn().mockResolvedValue(undefined)
const trailerRef = { value: { source: 'youtube', key: 'abcd1234567' } }
vi.mock('@/composables/portal/useTrailer', () => ({
  useTrailer: () => ({
    trailer: trailerRef,
    resolve: resolveTrailer,
    prefetch: vi.fn(),
    peek: vi.fn(),
    clear: vi.fn(() => {
      trailerRef.value = { source: 'youtube', key: 'abcd1234567' }
    }),
  }),
}))

vi.mock('@/composables/portal/useVideoPlayingFlag', () => ({
  useVideoPlayingFlag: () => ({ setPlaying: vi.fn(), release: vi.fn() }),
}))

import { useHeroBannerTrailer } from '@/composables/portal/useHeroBannerTrailer'

describe('useHeroBannerTrailer — autoplay-safe muted bootstrap', () => {
  beforeEach(() => {
    resolveTrailer.mockClear()
    trailerRef.value = { source: 'youtube', key: 'abcd1234567' }
    function FakePlayer(id, opts) {
      FakePlayer.lastOpts = opts
      FakePlayer.calls.push([id, opts])
      this.destroy = vi.fn()
      this.mute = vi.fn()
      this.unMute = vi.fn()
      this.playVideo = vi.fn()
    }
    FakePlayer.calls = []
    window.YT = { Player: FakePlayer }
  })

  it('always boots YT with playerVars.mute === 1 regardless of muted state', async () => {
    const hero = useHeroBannerTrailer()
    // Flip the user-facing muted flag off — this would have set
    // playerVars.mute=0 in the old behaviour and triggered the YT
    // pause overlay freeze.
    hero.setMuted(false)
    await hero.loadTrailer({ tmdb_id: 1, media_type: 'movie' })
    await nextTick()
    await flushPromises()
    await nextTick()

    expect(window.YT.Player.calls.length).toBe(1)
    const opts = window.YT.Player.calls[0][1]
    expect(opts.playerVars.mute).toBe(1)
    expect(opts.playerVars.autoplay).toBe(1)
  })
})
