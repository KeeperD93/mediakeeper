/**
 * Dashboard stat card: the figure counts up, shows at once under reduced motion, and a
 * count under way lands at once on the figure it was heading for when the setting is
 * turned on.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'

import StatCard from '@/components/dashboard/widgets/StatCard.vue'

vi.mock('vue-router', () => ({ useRouter: () => ({ push: vi.fn() }) }))

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

const mountCard = () => mount(StatCard, { props: { label: 'Plays', value: '12345' } })
const figure = wrapper => wrapper.find('.wg-stat-val').text()

describe('StatCard.vue — reduced motion', () => {
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ['performance', 'requestAnimationFrame', 'cancelAnimationFrame'] })
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
  })

  it('shows the value at once under reduced motion', async () => {
    stubReducedMotion(true)
    const wrapper = mountCard()
    await nextTick()
    expect(figure(wrapper)).toBe('12345')
    wrapper.unmount()
  })

  it('lands on the figure of a finished count when reduced motion is turned on midway', async () => {
    stubReducedMotion(false)
    const finished = mountCard()
    vi.advanceTimersByTime(1000)
    await nextTick()
    const last = figure(finished)
    finished.unmount()

    const wrapper = mountCard()
    vi.advanceTimersByTime(450)
    await nextTick()
    expect(figure(wrapper)).not.toBe(last)

    setting.flip(true)
    await nextTick()
    expect(figure(wrapper)).toBe(last)
    vi.advanceTimersByTime(1000)
    await nextTick()
    expect(figure(wrapper)).toBe(last)
    wrapper.unmount()
  })

  it('leaves a finished count alone when reduced motion is turned on', async () => {
    stubReducedMotion(false)
    const wrapper = mountCard()
    vi.advanceTimersByTime(1000)
    await nextTick()
    const last = figure(wrapper)

    setting.flip(true)
    await nextTick()
    expect(figure(wrapper)).toBe(last)
    wrapper.unmount()
  })
})
