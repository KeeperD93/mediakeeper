/**
 * News of the daily digest, both views: « Read more » opens the main item in place,
 * one other item opens at a time, and the compact view keeps unread items in sight
 * while the read ones wait behind « +N ».
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'

import DigestCompactNews from '../DigestCompactNews.vue'
import DigestNews from '../DigestNews.vue'

const news = (id, extra = {}) => ({
  id,
  title: `Test news ${id}`,
  content: 'First paragraph.',
  image_url: null,
  type: 'announcement',
  pinned: false,
  created_at: '2026-11-12T10:00:00Z',
  is_new: false,
  ...extra,
})

const LONG = 'First paragraph.\n\nSecond paragraph.\n\nThird paragraph.'

let wrapper

describe('DigestNews.vue (full view)', () => {
  afterEach(() => wrapper?.unmount())

  it('opens the rest of the main item in place, and reads it', async () => {
    wrapper = mount(DigestNews, { props: { news: [news(1, { content: LONG, is_new: true })] } })
    const button = wrapper.find('.dd-link-button')
    expect(wrapper.findAll('.dd-news-more')).toHaveLength(0)
    expect(button.attributes('aria-expanded')).toBe('false')

    await button.trigger('click')

    expect(wrapper.findAll('.dd-news-more').map(p => p.text())).toEqual([
      'Second paragraph.',
      'Third paragraph.',
    ])
    expect(button.attributes('aria-expanded')).toBe('true')
    expect(button.text()).toBe('portal.dailyDigest.news.readLess')
    expect(wrapper.emitted('read')).toEqual([[1]])
    expect(wrapper.emitted('seen')).toBeUndefined()
  })

  it('splits on line breaks when the text has no blank line', async () => {
    wrapper = mount(DigestNews, { props: { news: [news(1, { content: 'One.\nTwo.' })] } })
    expect(wrapper.find('.dd-news-text').text()).toBe('One.')
    await wrapper.find('.dd-link-button').trigger('click')
    expect(wrapper.find('.dd-news-more').text()).toBe('Two.')
  })

  it('has no « Read more » for a text that fits, and counts it as shown', () => {
    wrapper = mount(DigestNews, { props: { news: [news(1, { is_new: true })] } })
    expect(wrapper.find('.dd-link-button').exists()).toBe(false)
    expect(wrapper.emitted('seen')).toEqual([[1]])
  })

  it('opens one other item at a time, under its row', async () => {
    wrapper = mount(DigestNews, { props: { news: [news(1), news(2), news(3)] } })
    const rows = wrapper.findAll('.dd-more-row')

    await rows[0].trigger('click')
    await rows[1].trigger('click')

    expect(wrapper.findAll('.dd-more-body')).toHaveLength(1)
    expect(wrapper.findAll('.dd-more-item')[1].classes()).toContain('dd-more-item--open')
    expect(rows.map(row => row.attributes('aria-expanded'))).toEqual(['false', 'true'])
    expect(rows[1].find('.dd-chev').classes()).toContain('dd-chev--up')
    expect(wrapper.emitted('read')).toEqual([[2], [3]])

    await rows[1].trigger('click')
    expect(wrapper.find('.dd-more-body').exists()).toBe(false)
  })

  it('wears the colours of its type, the pin and the « New » marks', () => {
    wrapper = mount(DigestNews, {
      props: {
        news: [
          news(1, { pinned: true, is_new: true }),
          news(2, { type: 'maintenance', is_new: true }),
          news(3, { type: 'event' }),
          news(4, { type: 'unknown' }),
        ],
      },
    })
    expect(wrapper.find('.dd-news').classes()).toContain('dd-news--new')
    expect(wrapper.find('.dd-new-pill').exists()).toBe(true)
    expect(wrapper.find('.dd-badge--pin').exists()).toBe(true)
    const badges = wrapper.findAll('.dd-more-row .dd-badge')
    expect(badges.map(badge => badge.classes().join(' '))).toEqual([
      'dd-badge dd-badge--warn',
      'dd-badge dd-badge--event',
      'dd-badge',
    ])
    expect(badges[2].text()).toBe('portal.news.types.other')
    expect(wrapper.findAll('.dd-new-mini')).toHaveLength(1)
  })
})

describe('DigestCompactNews.vue (compact view)', () => {
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

  const titles = () => wrapper.findAll('.ddc-row-item .ddc-row-title').map(item => item.text())

  it('keeps unread items in sight and the read ones behind « +N »', async () => {
    wrapper = mount(DigestCompactNews, {
      props: { news: [news(1), news(2, { is_new: true }), news(3), news(4)] },
    })
    const more = wrapper.find('.ddc-row-more')
    expect(titles()).toEqual(['Test news 2'])
    expect(more.text()).toBe('portal.dailyDigest.news.moreCount:{"n":2}')
    expect(more.attributes('aria-expanded')).toBe('false')

    await more.trigger('click')

    expect(titles()).toEqual(['Test news 2', 'Test news 3', 'Test news 4'])
    expect(more.text()).toBe('portal.dailyDigest.news.hideMore')
  })

  it('leaves an item it just read in sight', async () => {
    const items = [news(1), news(2, { is_new: true }), news(3)]
    wrapper = mount(DigestCompactNews, { props: { news: items } })

    await wrapper.find('.ddc-row-item').trigger('click')
    await wrapper.setProps({ news: items.map(item => ({ ...item, is_new: false })) })

    expect(titles()).toEqual(['Test news 2'])
    expect(wrapper.find('.ddc-rowbody').exists()).toBe(true)
    expect(wrapper.emitted('read')).toEqual([[2]])
  })

  it('opens the rest of the main item in place', async () => {
    wrapper = mount(DigestCompactNews, { props: { news: [news(1, { content: LONG })] } })
    expect(wrapper.find('.ddc-text').classes()).toContain('ddc-text--clamp')

    await wrapper.find('.ddc-link-button').trigger('click')

    expect(wrapper.findAll('.ddc-text')).toHaveLength(3)
    expect(wrapper.find('.ddc-text').classes()).not.toContain('ddc-text--clamp')
    expect(wrapper.emitted('read')).toEqual([[1]])
  })

  it('counts a short main item as shown, with no « Read more »', () => {
    wrapper = mount(DigestCompactNews, { props: { news: [news(1)] } })
    expect(wrapper.find('.ddc-link-button').exists()).toBe(false)
    expect(wrapper.find('.ddc-morelist').exists()).toBe(false)
    expect(wrapper.emitted('seen')).toEqual([[1]])
  })
})
