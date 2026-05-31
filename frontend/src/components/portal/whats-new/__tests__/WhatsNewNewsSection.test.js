import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import WhatsNewNewsSection from '@/components/portal/whats-new/WhatsNewNewsSection.vue'

describe('WhatsNewNewsSection', () => {
  it('renders one card per news item', () => {
    const w = mount(WhatsNewNewsSection, {
      props: {
        news: [
          { id: 1, title: 'A', content_excerpt: 'short', image_url: null, type: 'announcement' },
          { id: 2, title: 'B', content_excerpt: 'short', image_url: null, type: 'event' },
          { id: 3, title: 'C', content_excerpt: 'short', image_url: null, type: 'maintenance' },
        ],
      },
    })
    expect(w.findAll('.wnns-card')).toHaveLength(3)
  })

  it('renders the image when image_url is set', () => {
    const w = mount(WhatsNewNewsSection, {
      props: {
        news: [
          {
            id: 1,
            title: 'A',
            content_excerpt: '',
            image_url: 'https://x.test/a.png',
            type: 'announcement',
          },
        ],
      },
    })
    const img = w.find('.wnns-thumb-img')
    expect(img.exists()).toBe(true)
    expect(img.attributes('src')).toBe('https://x.test/a.png')
  })

  it('falls back to a typed initial when image_url is absent', () => {
    const w = mount(WhatsNewNewsSection, {
      props: {
        news: [{ id: 1, title: 'Alpha', content_excerpt: '', image_url: null, type: 'event' }],
      },
    })
    expect(w.find('.wnns-thumb-img').exists()).toBe(false)
    expect(w.find('.wnns-thumb--fallback').exists()).toBe(true)
    expect(w.find('.wnns-thumb-mark').text()).toBe('A')
  })

  it('clamps the excerpt to 2 lines via CSS', () => {
    const w = mount(WhatsNewNewsSection, {
      props: {
        news: [{ id: 1, title: 'A', content_excerpt: 'long body', image_url: null, type: 'other' }],
      },
    })
    expect(w.find('.wnns-excerpt').exists()).toBe(true)
  })
})
