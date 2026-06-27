/**
 * Covers the "try another" fallback: when several candidate trailers are
 * supplied, the lightbox cycles to the next one (so a region-blocked
 * YouTube upload can be skipped without leaving the player). The button is
 * hidden when there is only a single candidate.
 */
import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'

vi.mock('lucide-vue-next', () => ({
  X: { name: 'XStub', template: '<i />' },
  SkipForward: { name: 'SkipForwardStub', template: '<i />' },
}))

import TrailerLightbox from '@/components/portal/TrailerLightbox.vue'

const A = { source: 'youtube', url: 'https://www.youtube.com/embed/AAA' }
const B = { source: 'youtube', url: 'https://www.youtube.com/embed/BBB' }

function mountWith(trailers) {
  return mount(TrailerLightbox, {
    props: { trailers },
    attachTo: document.body,
    global: { mocks: { $t: k => k } },
  })
}

describe('TrailerLightbox — try another candidate', () => {
  it('cycles to the next candidate when "try another" is clicked', async () => {
    const w = mountWith([A, B])
    expect(w.find('iframe').attributes('src')).toContain('/embed/AAA')
    expect(w.find('.pt-tlb-alt').exists()).toBe(true)

    await w.find('.pt-tlb-alt').trigger('click')
    expect(w.find('iframe').attributes('src')).toContain('/embed/BBB')

    // Wraps back around to the first candidate.
    await w.find('.pt-tlb-alt').trigger('click')
    expect(w.find('iframe').attributes('src')).toContain('/embed/AAA')
    w.unmount()
  })

  it('hides "try another" with a single candidate', () => {
    const w = mountWith([A])
    expect(w.find('.pt-tlb-alt').exists()).toBe(false)
    w.unmount()
  })

  it('still accepts the legacy single-trailer prop', () => {
    const w = mount(TrailerLightbox, {
      props: { trailer: A },
      attachTo: document.body,
      global: { mocks: { $t: k => k } },
    })
    expect(w.find('iframe').attributes('src')).toContain('/embed/AAA')
    expect(w.find('.pt-tlb-alt').exists()).toBe(false)
    w.unmount()
  })
})
