/**
 * usePrefersReducedMotion follows the device setting live and lets go of its
 * listener on unmount.
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { defineComponent, h } from 'vue'
import { mount } from '@vue/test-utils'
import { usePrefersReducedMotion } from '@/composables/usePrefersReducedMotion'

function mountWith() {
  let reduced
  const w = mount(
    defineComponent({
      setup() {
        reduced = usePrefersReducedMotion()
        return () => h('div')
      },
    }),
  )
  return { w, reduced }
}

describe('usePrefersReducedMotion', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('reads the setting on mount and follows its changes', () => {
    const mql = { matches: true, addEventListener: vi.fn(), removeEventListener: vi.fn() }
    vi.stubGlobal(
      'matchMedia',
      vi.fn(() => mql),
    )

    const { w, reduced } = mountWith()

    expect(window.matchMedia).toHaveBeenCalledWith('(prefers-reduced-motion: reduce)')
    expect(reduced.value).toBe(true)
    const [event, listener] = mql.addEventListener.mock.calls[0]
    expect(event).toBe('change')
    listener({ matches: false })
    expect(reduced.value).toBe(false)

    w.unmount()
    expect(mql.removeEventListener).toHaveBeenCalledWith('change', listener)
  })

  it('stays false where matchMedia does not exist', () => {
    const { w, reduced } = mountWith()

    expect(reduced.value).toBe(false)
    w.unmount()
  })
})
