/**
 * Covers useFocusTrap wired into TrailerLightbox: initial focus on the
 * close button, Escape routing through close, and body-scroll-lock cleanup.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

vi.mock('lucide-vue-next', () => ({
  X: { name: 'XStub', template: '<i />' },
}))

import TrailerLightbox from '@/components/portal/TrailerLightbox.vue'

const trailerEmby = {
  source: 'emby',
  url: 'http://example.test/trailer.mp4',
}

function buildLightbox(trailer = trailerEmby) {
  return mount(TrailerLightbox, {
    props: { trailer },
    attachTo: document.body,
    global: {
      mocks: { $t: key => key },
    },
  })
}

describe('TrailerLightbox — focus trap integration', () => {
  beforeEach(() => {
    document.body.style.overflow = ''
  })

  afterEach(() => {
    document.body.style.overflow = ''
  })

  it('moves initial focus onto the close button when the lightbox opens', async () => {
    const w = buildLightbox()
    await flushPromises()

    const closeBtn = document.querySelector('.pt-tlb-close')
    expect(closeBtn).not.toBeNull()
    expect(document.activeElement).toBe(closeBtn)

    w.unmount()
  })

  it('routes Escape to close and emits close exactly once', async () => {
    const w = buildLightbox()
    await flushPromises()

    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))
    await flushPromises()

    expect(w.emitted('close')).toBeTruthy()
    expect(w.emitted('close').length).toBe(1)

    w.unmount()
  })

  it('restores body overflow when the lightbox unmounts', async () => {
    const w = buildLightbox()
    await flushPromises()
    expect(document.body.style.overflow).toBe('hidden')

    w.unmount()
    expect(document.body.style.overflow).toBe('')
  })
})
