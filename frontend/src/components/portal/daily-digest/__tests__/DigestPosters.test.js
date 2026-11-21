/**
 * « New in the library » rail of the daily digest: arrows move it by three posters and
 * light up only where there is something to reach; a poster opens its page.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount, RouterLinkStub } from '@vue/test-utils'
import { ref } from 'vue'

import DigestPosters from '../DigestPosters.vue'

vi.mock('vue-i18n', async importOriginal => ({
  ...(await importOriginal()),
  useI18n: () => ({ locale: ref('fr'), t: key => key }),
}))

const item = (n, extra = {}) => ({
  tmdb_id: 12345 + n,
  emby_item_id: `e${n}`,
  title: `Test Movie ${n}`,
  year: '2024',
  media_type: 'movie',
  poster_url: `/api/emby/image/e${n}?type=Primary`,
  date_created: '2026-11-12',
  ...extra,
})

const rect = (left, width) => ({ left, width, right: left + width })

let wrapper

async function render(items) {
  wrapper = mount(DigestPosters, {
    props: { items },
    global: { stubs: { 'router-link': RouterLinkStub } },
  })
  await flushPromises()
  const track = wrapper.find('.dd-posters').element
  const [first, second] = track.children
  track.getBoundingClientRect = () => rect(0, 780)
  first.getBoundingClientRect = () => rect(0, 140)
  second.getBoundingClientRect = () => rect(152, 140)
  track.scrollBy = vi.fn()
  return track
}

function scrollTo(track, left) {
  Object.defineProperty(track, 'scrollLeft', { value: left, configurable: true })
  Object.defineProperty(track, 'clientWidth', { value: 780, configurable: true })
  Object.defineProperty(track, 'scrollWidth', { value: 1812, configurable: true })
  return wrapper.find('.dd-posters').trigger('scroll')
}

describe('DigestPosters.vue', () => {
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
    wrapper?.unmount()
    vi.unstubAllGlobals()
  })

  it('moves by three posters per click', async () => {
    const track = await render(Array.from({ length: 12 }, (_, n) => item(n)))
    await scrollTo(track, 456)

    await wrapper.find('.dd-pnav--next').trigger('click')
    await wrapper.find('.dd-pnav--prev').trigger('click')

    // Posters of 140 px, 12 px apart.
    expect(track.scrollBy.mock.calls).toEqual([[{ left: 456 }], [{ left: -456 }]])
  })

  it('lights each arrow only where there is something to reach', async () => {
    const track = await render(Array.from({ length: 12 }, (_, n) => item(n)))
    const prev = () => wrapper.find('.dd-pnav--prev').attributes('disabled')
    const next = () => wrapper.find('.dd-pnav--next').attributes('disabled')

    await scrollTo(track, 0)
    expect([prev(), next()]).toEqual(['', undefined])

    await scrollTo(track, 456)
    expect([prev(), next()]).toEqual([undefined, undefined])

    await scrollTo(track, 1032)
    expect([prev(), next()]).toEqual([undefined, ''])
  })

  it('opens the page of a poster and leaves the window; one without an id opens nothing', async () => {
    await render([item(1), item(2, { tmdb_id: null, poster_url: null })])
    const links = wrapper.findAllComponents(RouterLinkStub)
    expect(links).toHaveLength(1)
    expect(links[0].props('to')).toEqual({
      name: 'portal-media-detail',
      params: { type: 'movie', id: 12346 },
    })

    await links[0].trigger('click')
    expect(wrapper.emitted('leave')).toHaveLength(1)
    expect(wrapper.find('.dd-poster-fallback').text()).toBe('T')
  })

  it('names a series under its title, and counts the additions', async () => {
    await render([item(1), item(2, { media_type: 'tv', year: '' })])
    expect(wrapper.find('.dd-count').text()).toBe('2')
    expect(wrapper.findAll('.dd-poster-cap small').map(small => small.text())).toEqual([
      '2024',
      'portal.dailyDigest.posters.series',
    ])
  })
})
