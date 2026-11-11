/**
 * Particles of the sign-in page: they move only while the theme shows them and the
 * device does not ask for reduced motion, and follow either setting live.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { defineComponent, h, ref } from 'vue'

import { useLoginParticles } from '@/composables/useLoginParticles'

let ctx
let frames
let reducedQuery

function stubReducedMotion(matches) {
  const listeners = new Set()
  reducedQuery = {
    matches,
    addEventListener: (_event, handler) => listeners.add(handler),
    removeEventListener: (_event, handler) => listeners.delete(handler),
    flip(next) {
      reducedQuery.matches = next
      for (const handler of listeners) handler({ matches: next })
    },
  }
  vi.stubGlobal(
    'matchMedia',
    vi.fn(() => reducedQuery),
  )
}

function mountPage(enabled = ref(true)) {
  const wrapper = mount(
    defineComponent({
      setup() {
        const pageRef = ref(null)
        const canvasRef = ref(null)
        useLoginParticles(canvasRef, pageRef, enabled)
        return () => h('main', { ref: pageRef }, [h('canvas', { ref: canvasRef })])
      },
    }),
  )
  return { wrapper, enabled }
}

beforeEach(() => {
  ctx = { clearRect: vi.fn(), beginPath: vi.fn(), arc: vi.fn(), fill: vi.fn() }
  vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(ctx)
  frames = { request: vi.fn(() => 7), cancel: vi.fn() }
  vi.stubGlobal('requestAnimationFrame', frames.request)
  vi.stubGlobal('cancelAnimationFrame', frames.cancel)
  vi.stubGlobal(
    'ResizeObserver',
    class {
      observe() {}
      disconnect() {}
    },
  )
})

afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

describe('useLoginParticles', () => {
  it('moves the particles when nothing asks otherwise', () => {
    stubReducedMotion(false)
    const { wrapper } = mountPage()
    expect(frames.request).toHaveBeenCalledTimes(1)
    wrapper.unmount()
    expect(frames.cancel).toHaveBeenCalledWith(7)
  })

  it('never starts them under reduced motion', () => {
    stubReducedMotion(true)
    const { wrapper } = mountPage()
    expect(frames.request).not.toHaveBeenCalled()
    expect(HTMLCanvasElement.prototype.getContext).not.toHaveBeenCalled()
    wrapper.unmount()
  })

  it('stops and clears them when reduced motion is turned on, and starts them again', () => {
    stubReducedMotion(false)
    const { wrapper } = mountPage()

    ctx.clearRect.mockClear()
    reducedQuery.flip(true)
    expect(frames.cancel).toHaveBeenCalledWith(7)
    expect(ctx.clearRect).toHaveBeenCalledTimes(1)

    reducedQuery.flip(false)
    expect(frames.request).toHaveBeenCalledTimes(2)
    wrapper.unmount()
  })

  it('starts them again even when the setting comes back before the page updates', () => {
    stubReducedMotion(true)
    const { wrapper } = mountPage()
    reducedQuery.flip(false)
    expect(frames.request).toHaveBeenCalledTimes(1)
    wrapper.unmount()
  })

  it('follows the theme setting', () => {
    stubReducedMotion(false)
    const { wrapper, enabled } = mountPage(ref(false))
    expect(frames.request).not.toHaveBeenCalled()

    enabled.value = true
    expect(frames.request).toHaveBeenCalledTimes(1)
    enabled.value = false
    expect(frames.cancel).toHaveBeenCalledWith(7)
    wrapper.unmount()
  })
})
