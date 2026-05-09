/**
 * Verifies that the hero autoplay composable honours the
 * `prefers-reduced-motion: reduce` user preference: no setInterval is
 * started when reduce is initially true, and the timer toggles when the
 * preference flips at runtime. Manual goTo() must still work in both
 * cases. Listeners are cleaned up on unmount.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { defineComponent, h, ref } from 'vue'

import { useHeroAutoplay } from '@/composables/useHeroAutoplay'

function buildMatchMedia(initialMatches = false) {
  const listeners = new Set()
  const mql = {
    matches: initialMatches,
    media: '(prefers-reduced-motion: reduce)',
    addEventListener: vi.fn((_evt, handler) => listeners.add(handler)),
    removeEventListener: vi.fn((_evt, handler) => listeners.delete(handler)),
    dispatchChange(matches) {
      mql.matches = matches
      for (const handler of listeners) handler({ matches })
    },
    listeners,
  }
  window.matchMedia = vi.fn(() => mql)
  return mql
}

function buildHarness(sessionsRef) {
  let api
  const wrapper = mount(
    defineComponent({
      setup() {
        api = useHeroAutoplay(sessionsRef, 1000)
        return () => h('div')
      },
    }),
  )
  return { wrapper, get: () => api }
}

beforeEach(() => {
  vi.useFakeTimers()
})

afterEach(() => {
  vi.useRealTimers()
  delete window.matchMedia
})

describe('useHeroAutoplay — prefers-reduced-motion', () => {
  it('does NOT start autoplay when reduce is initially true', () => {
    buildMatchMedia(true)
    const sessions = ref([{ id: 'a' }, { id: 'b' }, { id: 'c' }])
    const { wrapper, get } = buildHarness(sessions)

    expect(get().idx.value).toBe(0)
    vi.advanceTimersByTime(5000)
    expect(get().idx.value).toBe(0)
    wrapper.unmount()
  })

  it('starts autoplay when reduce is initially false', () => {
    buildMatchMedia(false)
    const sessions = ref([{ id: 'a' }, { id: 'b' }, { id: 'c' }])
    const { wrapper, get } = buildHarness(sessions)

    vi.advanceTimersByTime(1000)
    expect(get().idx.value).toBe(1)
    vi.advanceTimersByTime(1000)
    expect(get().idx.value).toBe(2)
    wrapper.unmount()
  })

  it('stops autoplay live when the preference flips to reduce', () => {
    const mql = buildMatchMedia(false)
    const sessions = ref([{ id: 'a' }, { id: 'b' }, { id: 'c' }])
    const { wrapper, get } = buildHarness(sessions)

    vi.advanceTimersByTime(1000)
    expect(get().idx.value).toBe(1)

    mql.dispatchChange(true)
    vi.advanceTimersByTime(5000)
    expect(get().idx.value).toBe(1)
    wrapper.unmount()
  })

  it('manual goTo still works under reduced motion and unmount removes the listener', () => {
    const mql = buildMatchMedia(true)
    const sessions = ref([{ id: 'a' }, { id: 'b' }, { id: 'c' }])
    const { wrapper, get } = buildHarness(sessions)

    get().goTo(2)
    expect(get().idx.value).toBe(2)
    vi.advanceTimersByTime(3000)
    expect(get().idx.value).toBe(2)

    expect(mql.addEventListener).toHaveBeenCalledTimes(1)
    wrapper.unmount()
    expect(mql.removeEventListener).toHaveBeenCalledTimes(1)
    expect(mql.listeners.size).toBe(0)
  })
})
