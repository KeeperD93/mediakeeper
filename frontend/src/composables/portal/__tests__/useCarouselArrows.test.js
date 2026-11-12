/**
 * useCarouselArrows: an arrow moves the track by a page of whole cards and leaves the
 * motion to the track's CSS (smooth, or a jump under reduced motion).
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { defineComponent, h } from 'vue'

import { useCarouselArrows } from '@/composables/portal/useCarouselArrows'

const rect = (left, width) => ({ left, width, right: left + width })

function mountCarousel() {
  let api
  const wrapper = mount(
    defineComponent({
      setup() {
        api = useCarouselArrows()
        return () => h('div', { ref: api.trackRef }, [h('span'), h('span')])
      },
    }),
  )
  const track = api.trackRef.value
  const [first, second] = track.children
  track.getBoundingClientRect = () => rect(0, 500)
  first.getBoundingClientRect = () => rect(0, 100)
  second.getBoundingClientRect = () => rect(112, 100)
  track.scrollBy = vi.fn()
  return { wrapper, api, track }
}

describe('useCarouselArrows — scroll', () => {
  beforeEach(() => {
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
  })

  it('moves by the cards in view, without forcing a smooth slide', () => {
    const { wrapper, api, track } = mountCarousel()

    api.scroll(1)
    api.scroll(-1)

    // Cards of 100 px, 12 px apart: four of them fit in 500 px.
    expect(track.scrollBy.mock.calls).toEqual([[{ left: 448 }], [{ left: -448 }]])
    wrapper.unmount()
  })
})
