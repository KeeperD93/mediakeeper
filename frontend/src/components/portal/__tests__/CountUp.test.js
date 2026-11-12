/**
 * CountUp: the figure counts up to its value, shows it at once under reduced motion,
 * and a count under way ends at once when the setting is turned on.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'

import CountUp from '@/components/portal/CountUp.vue'

let setting

function stubReducedMotion(matches) {
  const listeners = new Set()
  setting = {
    matches,
    addEventListener: (_event, handler) => listeners.add(handler),
    removeEventListener: (_event, handler) => listeners.delete(handler),
    flip(next) {
      setting.matches = next
      for (const handler of listeners) handler({ matches: next })
    },
  }
  vi.stubGlobal(
    'matchMedia',
    vi.fn(() => setting),
  )
}

const mountCount = () =>
  mount(CountUp, { props: { value: 1000, duration: 800, formatter: n => String(Math.round(n)) } })

describe('CountUp.vue — reduced motion', () => {
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ['performance', 'requestAnimationFrame', 'cancelAnimationFrame'] })
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
  })

  it('counts up to its value', async () => {
    stubReducedMotion(false)
    const wrapper = mountCount()
    vi.advanceTimersByTime(400)
    await nextTick()
    expect(Number(wrapper.text())).toBeGreaterThan(0)
    expect(Number(wrapper.text())).toBeLessThan(1000)
    vi.advanceTimersByTime(600)
    await nextTick()
    expect(wrapper.text()).toBe('1000')
    wrapper.unmount()
  })

  it('shows the value at once under reduced motion', async () => {
    stubReducedMotion(true)
    const wrapper = mountCount()
    await nextTick()
    expect(wrapper.text()).toBe('1000')
    wrapper.unmount()
  })

  it('ends a count under way when reduced motion is turned on', async () => {
    stubReducedMotion(false)
    const wrapper = mountCount()
    vi.advanceTimersByTime(400)

    await nextTick()
    expect(wrapper.text()).not.toBe('1000')

    setting.flip(true)
    await nextTick()
    expect(wrapper.text()).toBe('1000')
    vi.advanceTimersByTime(600)
    await nextTick()
    expect(wrapper.text()).toBe('1000')
    wrapper.unmount()
  })
})
