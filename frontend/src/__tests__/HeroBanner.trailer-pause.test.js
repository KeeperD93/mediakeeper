/**
 * Regression: opening the hero trailer must pause the parent carousel
 * rotation (emit `trailer-open`) and resume it on close (emit
 * `trailer-close`). Guards against the dead sound-on/off wiring that let
 * the open trailer keep following the rotating hero.
 */
import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'

vi.mock('@/composables/portal/useRequestStatus', () => ({
  useRequestStatus: () => ({ getStatus: vi.fn(() => null), checkStatus: vi.fn() }),
}))

vi.mock('@/composables/portal/useTrailer', async () => {
  const { ref } = await vi.importActual('vue')
  const descriptor = { source: 'youtube', url: 'https://x', key: 'abc', name: 'Trailer' }
  return {
    useTrailer: () => ({
      trailer: ref(descriptor),
      candidates: ref([descriptor]),
      resolve: vi.fn(),
      prefetch: vi.fn(),
    }),
  }
})

vi.mock('@/components/portal/TrailerLightbox.vue', () => ({
  default: { name: 'TrailerLightbox', emits: ['close'], template: '<div />' },
}))

vi.mock('lucide-vue-next', () => ({
  Clock: { name: 'ClockStub', template: '<i />' },
  Info: { name: 'InfoStub', template: '<i />' },
  Plus: { name: 'PlusStub', template: '<i />' },
  Video: { name: 'VideoStub', template: '<i />' },
}))

import HeroBanner from '@/components/portal/HeroBanner.vue'

// emby_url set so the request CTA is hidden — keeps the test focused on
// the trailer button.
const item = { id: 1, tmdb_id: 1, title: 'X', media_type: 'movie', emby_url: 'http://emby/x' }

describe('HeroBanner — trailer pauses the hero rotation', () => {
  it('emits trailer-open on open and trailer-close on close', async () => {
    const w = mount(HeroBanner, { props: { item } })

    await w.get('.pt-hero-btn--trailer').trigger('click')
    expect(w.emitted('trailer-open')).toBeTruthy()
    expect(w.emitted('trailer-close')).toBeFalsy()

    w.findComponent({ name: 'TrailerLightbox' }).vm.$emit('close')
    expect(w.emitted('trailer-close')).toBeTruthy()
  })
})
