/**
 * useLongPress — coverage of the three branches MobileDashboard.vue
 * relies on:
 *
 * 1. Callback fires when the touch is held still for ``delay`` ms.
 * 2. Callback is cancelled if the pointer moves more than the
 *    ``moveThreshold`` pixel budget.
 * 3. Callback is cancelled when touchend fires before the timer.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { mount } from '@vue/test-utils'

import { useLongPress } from '@/composables/useLongPress'

function makeHost(callback, options) {
  const captured = {}
  const Host = defineComponent({
    setup() {
      captured.api = useLongPress(callback, options)
      return () => h('div')
    },
  })
  const wrapper = mount(Host)
  return { wrapper, api: captured.api }
}

function touch(clientX, clientY) {
  return { touches: [{ clientX, clientY }] }
}

describe('useLongPress', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('fires the callback after the delay when held still', () => {
    const cb = vi.fn()
    const { api } = makeHost(cb, { delay: 400 })

    api.onTouchStart(touch(100, 100))
    vi.advanceTimersByTime(399)
    expect(cb).not.toHaveBeenCalled()

    vi.advanceTimersByTime(2)
    expect(cb).toHaveBeenCalledTimes(1)
  })

  it('cancels when the pointer moves beyond the threshold', () => {
    const cb = vi.fn()
    const { api } = makeHost(cb, { delay: 400, moveThreshold: 10 })

    api.onTouchStart(touch(100, 100))
    api.onTouchMove(touch(115, 100))
    vi.advanceTimersByTime(500)

    expect(cb).not.toHaveBeenCalled()
  })

  it('does not cancel when movement stays within the threshold', () => {
    const cb = vi.fn()
    const { api } = makeHost(cb, { delay: 400, moveThreshold: 10 })

    api.onTouchStart(touch(100, 100))
    api.onTouchMove(touch(105, 102))
    vi.advanceTimersByTime(500)

    expect(cb).toHaveBeenCalledTimes(1)
  })

  it('cancels when touchend fires before the timer elapses', () => {
    const cb = vi.fn()
    const { api } = makeHost(cb, { delay: 400 })

    api.onTouchStart(touch(50, 50))
    vi.advanceTimersByTime(200)
    api.onTouchEnd()
    vi.advanceTimersByTime(500)

    expect(cb).not.toHaveBeenCalled()
  })

  it('imperative cancel() clears the in-flight timer', () => {
    const cb = vi.fn()
    const { api } = makeHost(cb, { delay: 400 })

    api.onTouchStart(touch(0, 0))
    api.cancel()
    vi.advanceTimersByTime(500)

    expect(cb).not.toHaveBeenCalled()
  })
})
