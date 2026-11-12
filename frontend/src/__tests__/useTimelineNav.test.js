/**
 * Watchlist timeline: the month and today links glide to their row, or jump to it
 * when the device asks for reduced motion.
 */
import { afterEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { defineComponent, h, ref } from 'vue'

import { useTimelineNav } from '@/components/watchlist/WlTimelineView/useTimelineNav'

vi.mock('vue-i18n', () => ({ useI18n: () => ({ locale: ref('fr') }) }))

function mountTimeline(reduced) {
  vi.stubGlobal(
    'matchMedia',
    vi.fn(() => ({
      matches: reduced,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    })),
  )
  let nav
  const wrapper = mount(
    defineComponent({
      setup() {
        nav = useTimelineNav(ref([]))
        return () =>
          h('div', { ref: nav.scrollRef }, [
            h('div', { 'data-date': '2026-01-15' }),
            h('div', { 'data-date': nav.NOW }),
          ])
      },
    }),
  )
  const container = nav.scrollRef.value
  container.scrollTo = vi.fn()
  // The first jump to today, on opening, never glides.
  const root = ref({ offsetParent: {}, getBoundingClientRect: () => ({ width: 1, height: 1 }) })
  nav.doAutoScroll(root)
  container.scrollTo.mockClear()
  return { wrapper, nav, container }
}

const behaviors = container => container.scrollTo.mock.calls.map(([options]) => options.behavior)

describe('useTimelineNav — scrolling', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('glides to a month and to today', () => {
    const { wrapper, nav, container } = mountTimeline(false)
    nav.goMonth('2026-01-01')
    nav.goToday()
    expect(behaviors(container)).toEqual(['smooth', 'smooth'])
    wrapper.unmount()
  })

  it('jumps there under reduced motion', () => {
    const { wrapper, nav, container } = mountTimeline(true)
    nav.goMonth('2026-01-01')
    nav.goToday()
    expect(behaviors(container)).toEqual(['auto', 'auto'])
    wrapper.unmount()
  })
})
