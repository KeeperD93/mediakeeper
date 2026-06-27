/**
 * Covers the HeroBanner request CTA: it must reflect the request status
 * (muted "Pending" when already requested), fall back to "Request"
 * otherwise, hide entirely for titles already on Emby, and prime the
 * status cache for the current item.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ref } from 'vue'
import { mount } from '@vue/test-utils'

const getStatus = vi.fn()
const checkStatus = vi.fn()

vi.mock('@/composables/portal/useRequestStatus', () => ({
  useRequestStatus: () => ({ getStatus, checkStatus }),
}))

vi.mock('@/composables/portal/useTrailer', () => ({
  useTrailer: () => ({
    trailer: ref(null),
    candidates: ref([]),
    resolve: vi.fn(),
    prefetch: vi.fn(),
  }),
}))

vi.mock('@/components/portal/TrailerLightbox.vue', () => ({
  default: { name: 'TrailerLightbox', template: '<div />' },
}))

vi.mock('lucide-vue-next', () => ({
  Clock: { name: 'ClockStub', template: '<i />' },
  Info: { name: 'InfoStub', template: '<i />' },
  Plus: { name: 'PlusStub', template: '<i />' },
  Video: { name: 'VideoStub', template: '<i />' },
}))

import HeroBanner from '@/components/portal/HeroBanner.vue'
import { REQUEST_STATUS } from '@/constants/requests'

const movieItem = {
  id: 12345,
  tmdb_id: 12345,
  title: 'Test Movie',
  media_type: 'movie',
  // no emby_url → the request CTA is surfaced
}

function buildHero(item = movieItem) {
  return mount(HeroBanner, { props: { item } })
}

describe('HeroBanner — request CTA reflects request status', () => {
  beforeEach(() => {
    getStatus.mockReset()
    checkStatus.mockReset()
    getStatus.mockReturnValue(null)
  })

  it('shows the Request button and emits request when the title is not yet requested', async () => {
    const w = buildHero()

    const btn = w.get('.pt-hero-btn--play')
    expect(btn.text()).toContain('portal.card.requestBtn')
    expect(w.find('.pt-hero-btn--pending').exists()).toBe(false)

    await btn.trigger('click')
    expect(w.emitted('request')).toBeTruthy()
  })

  it('shows a muted Pending button with no request emit when an active request exists', async () => {
    getStatus.mockReturnValue({ status: REQUEST_STATUS.PENDING })
    const w = buildHero()

    const pending = w.get('.pt-hero-btn--pending')
    expect(pending.text()).toContain('portal.card.pendingBtn')
    expect(pending.attributes('aria-disabled')).toBe('true')
    expect(w.find('.pt-hero-btn--play').exists()).toBe(false)

    await pending.trigger('click')
    expect(w.emitted('request')).toBeFalsy()
  })

  it('treats an approved request as pending too', () => {
    getStatus.mockReturnValue({ status: REQUEST_STATUS.APPROVED })
    const w = buildHero()
    expect(w.find('.pt-hero-btn--pending').exists()).toBe(true)
  })

  it('hides the request CTA entirely for a title already on Emby', () => {
    const w = buildHero({ ...movieItem, emby_url: 'http://emby/x' })
    expect(w.find('.pt-hero-btn--play').exists()).toBe(false)
    expect(w.find('.pt-hero-btn--pending').exists()).toBe(false)
  })

  it('primes the request-status cache for the current item on mount', () => {
    buildHero()
    expect(checkStatus).toHaveBeenCalled()
  })
})
