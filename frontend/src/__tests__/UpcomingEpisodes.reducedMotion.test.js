/**
 * The upcoming episodes strip follows the device's reduced-motion setting live,
 * through the shared usePrefersReducedMotion: the looping marquee shows each
 * series twice, the hand-scrolled strip of reduced motion only once.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { nextTick } from 'vue'

import { usePrefersReducedMotion } from '@/composables/usePrefersReducedMotion'

vi.mock('@/i18n', () => ({ getLocale: () => 'fr' }))

const apiGet = vi.fn()

vi.mock('@/composables/useApi', () => ({ useApi: () => ({ apiGet }) }))

vi.mock('vue-i18n', async () => {
  const { ref } = await vi.importActual('vue')
  return { useI18n: () => ({ t: key => key, locale: ref('fr') }) }
})

vi.mock('@/composables/usePrefersReducedMotion', async importOriginal => {
  const actual = await importOriginal()
  return { usePrefersReducedMotion: vi.fn(actual.usePrefersReducedMotion) }
})

import UpcomingEpisodes from '@/components/dashboard/UpcomingEpisodes.vue'

const EPISODES = [
  { series_name: 'Sample Show', season: 1, episode: 1, air_date: '2026-07-01', tmdb_id: 1 },
  { series_name: 'Test Series', season: 2, episode: 3, air_date: '2026-07-02', tmdb_id: 2 },
]

function stubMatchMedia(matches) {
  const listeners = new Set()
  const mql = {
    matches,
    addEventListener: vi.fn((_event, handler) => listeners.add(handler)),
    removeEventListener: vi.fn((_event, handler) => listeners.delete(handler)),
    flip(next) {
      mql.matches = next
      for (const handler of listeners) handler({ matches: next })
    },
    listeners,
  }
  vi.stubGlobal(
    'matchMedia',
    vi.fn(() => mql),
  )
  return mql
}

async function mountStrip() {
  apiGet.mockResolvedValueOnce(EPISODES)
  const wrapper = mount(UpcomingEpisodes)
  await flushPromises()
  return wrapper
}

const shown = wrapper => ({
  cards: wrapper.findAll('.uc-card').length,
  seams: wrapper.findAll('.uc-sep').length,
})

describe('UpcomingEpisodes — reduced motion', () => {
  beforeEach(() => {
    apiGet.mockReset()
    usePrefersReducedMotion.mockClear()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('reads the setting through the shared composable', async () => {
    stubMatchMedia(false)
    const wrapper = await mountStrip()
    expect(usePrefersReducedMotion).toHaveBeenCalledTimes(1)
    expect(window.matchMedia).toHaveBeenCalledTimes(1)
    wrapper.unmount()
  })

  it('shows each series once under reduced motion, twice in the marquee', async () => {
    stubMatchMedia(true)
    const reduced = await mountStrip()
    expect(shown(reduced)).toEqual({ cards: 2, seams: 1 })
    reduced.unmount()

    stubMatchMedia(false)
    const moving = await mountStrip()
    expect(shown(moving)).toEqual({ cards: 4, seams: 2 })
    moving.unmount()
  })

  it('follows the setting when it changes, and lets go of it on unmount', async () => {
    const mql = stubMatchMedia(false)
    const wrapper = await mountStrip()

    mql.flip(true)
    await nextTick()
    expect(shown(wrapper)).toEqual({ cards: 2, seams: 1 })

    mql.flip(false)
    await nextTick()
    expect(shown(wrapper)).toEqual({ cards: 4, seams: 2 })

    wrapper.unmount()
    expect(mql.listeners.size).toBe(0)
  })
})
