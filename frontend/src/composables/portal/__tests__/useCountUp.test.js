/**
 * useCountUp — coverage of the three branches the leaderboard relies on:
 *
 * 1. duration=0 snaps to the target on mount.
 * 2. prefers-reduced-motion: reduce snaps to the target on mount.
 * 3. With a real duration, the displayed value lands strictly between
 *    zero and the target at mid-progress and exactly on the target
 *    when the duration elapses.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h, nextTick } from 'vue'
import { mount } from '@vue/test-utils'

import { useCountUp } from '@/composables/portal/useCountUp'

function makeHost(target, options) {
  const captured = {}
  const Host = defineComponent({
    setup() {
      captured.api = useCountUp(target, options)
      return () => h('span', captured.api.displayed.value.toString())
    },
  })
  const wrapper = mount(Host)
  return { wrapper, get displayed() { return captured.api.displayed.value } }
}

function stubMatchMedia(matches) {
  vi.stubGlobal('matchMedia', vi.fn(() => ({
    matches,
    media: '(prefers-reduced-motion: reduce)',
    addEventListener: () => {},
    removeEventListener: () => {},
  })))
}

describe('useCountUp', () => {
  beforeEach(() => {
    stubMatchMedia(false)
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
  })

  it('snaps to target instantly when duration is 0', async () => {
    const host = makeHost(100, { duration: 0 })
    await nextTick()
    expect(host.displayed).toBe(100)
  })

  it('snaps to target when prefers-reduced-motion is on', async () => {
    stubMatchMedia(true)
    const host = makeHost(750, { duration: 1200 })
    await nextTick()
    expect(host.displayed).toBe(750)
  })

  it('lands between 0 and target mid-animation and reaches target at the end', async () => {
    vi.useFakeTimers({ toFake: ['performance', 'requestAnimationFrame', 'cancelAnimationFrame'] })
    const host = makeHost(1000, { duration: 1200 })
    await nextTick()

    // First frame: progress ≈ 0 → displayed ≈ 0.
    vi.advanceTimersByTime(16)
    expect(host.displayed).toBeGreaterThanOrEqual(0)
    expect(host.displayed).toBeLessThan(1000)

    // Mid-progress (~600 ms): displayed strictly between 0 and target.
    vi.advanceTimersByTime(600)
    expect(host.displayed).toBeGreaterThan(0)
    expect(host.displayed).toBeLessThan(1000)

    // End of animation: displayed equals the target exactly.
    vi.advanceTimersByTime(800)
    expect(host.displayed).toBe(1000)
  })
})
