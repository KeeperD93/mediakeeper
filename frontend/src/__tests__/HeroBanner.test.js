/**
 * Covers the HeroBanner CTA: it must reflect the request status (muted
 * "Pending" when already requested, "Request again" once refused), fall
 * back to "Request" otherwise, offer "Play" for titles already on Emby, and
 * prime the status cache for the current item. The dots that pick a title
 * are labelled buttons.
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
  RotateCcw: { name: 'RotateCcwStub', template: '<i />' },
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

function buildHero(item = movieItem, props = {}) {
  return mount(HeroBanner, { props: { item, ...props } })
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

  it('offers Play, opening Emby in a new tab, for a title already on Emby', () => {
    // Even with an open request, a title on Emby only offers Play.
    getStatus.mockReturnValue({ status: REQUEST_STATUS.PENDING })
    const w = buildHero({ ...movieItem, emby_url: 'http://emby.invalid/item' })
    const play = w.get('a.pt-hero-btn--play')
    expect(play.text()).toContain('portal.hero.play')
    expect(play.attributes('href')).toBe('http://emby.invalid/item')
    expect(play.attributes('target')).toBe('_blank')
    expect(play.attributes('rel')).toBe('noopener noreferrer')
    expect(w.find('button.pt-hero-btn--play').exists()).toBe(false)
    expect(w.find('.pt-hero-btn--pending').exists()).toBe(false)
  })

  it('shows no button at all when the Emby link is unsafe', () => {
    getStatus.mockReturnValue({ status: REQUEST_STATUS.PENDING })
    const w = buildHero({ ...movieItem, emby_url: 'javascript:alert(1)' })
    expect(w.find('.pt-hero-btn--play').exists()).toBe(false)
    expect(w.find('.pt-hero-btn--pending').exists()).toBe(false)
  })

  it('offers Request again for a refused title', async () => {
    getStatus.mockReturnValue({ status: REQUEST_STATUS.REJECTED })
    const w = buildHero()

    const btn = w.get('button.pt-hero-btn--play')
    expect(btn.text()).toContain('portal.detail.reRequest')
    expect(btn.findComponent({ name: 'RotateCcwStub' }).exists()).toBe(true)
    expect(btn.findComponent({ name: 'PlusStub' }).exists()).toBe(false)

    await btn.trigger('click')
    expect(w.emitted('request')).toEqual([[movieItem]])
  })

  it('primes the request-status cache for the current item on mount', () => {
    buildHero()
    expect(checkStatus).toHaveBeenCalled()
  })
})

describe('HeroBanner — dots', () => {
  beforeEach(() => {
    getStatus.mockReturnValue(null)
  })

  it('names each dot, marks the current one and jumps to the one clicked', async () => {
    const w = buildHero(movieItem, { currentIndex: 1, totalItems: 3 })

    const dots = w.findAll('.pt-hero-dot')
    expect(dots.map(d => d.element.tagName)).toEqual(['BUTTON', 'BUTTON', 'BUTTON'])
    expect(dots[0].attributes('type')).toBe('button')
    expect(dots[0].attributes('aria-label')).toBe('portal.hero.goTo:{"n":1,"total":3}')
    expect(dots.map(d => d.attributes('aria-current'))).toEqual([undefined, 'true', undefined])

    await dots[2].trigger('click')
    expect(w.emitted('goto')).toEqual([[2]])
  })

  it('shows no dots for a single title', () => {
    const w = buildHero(movieItem, { totalItems: 1 })
    expect(w.find('.pt-hero-dots').exists()).toBe(false)
  })
})
