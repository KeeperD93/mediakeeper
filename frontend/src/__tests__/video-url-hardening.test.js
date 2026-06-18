/**
 * URL-sink hardening for video extras: the trailer iframe only embeds a
 * validated absolute https URL, and the YouTube watch link encodes the video
 * key so a hostile key can't smuggle extra query parameters into the href.
 */
import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'

vi.mock('lucide-vue-next', () => ({
  X: { name: 'XStub', template: '<i />' },
  Play: { name: 'PlayStub', template: '<i />' },
}))
vi.mock('vue-i18n', () => ({ useI18n: () => ({ t: k => k, te: () => false }) }))
vi.mock('@/utils/datetime', () => ({ localizedDate: () => '' }))

import TrailerLightbox from '@/components/portal/TrailerLightbox.vue'
import DetailExtras from '@/components/portal/detail/DetailExtras.vue'

function mountTrailer(trailer) {
  return mount(TrailerLightbox, {
    props: { trailer },
    attachTo: document.body,
    global: { mocks: { $t: k => k } },
  })
}

describe('TrailerLightbox — iframe src hardening', () => {
  it('embeds a validated https trailer URL', () => {
    const w = mountTrailer({ source: 'youtube', url: 'https://www.youtube.com/embed/abc123' })
    const iframe = w.find('iframe')
    expect(iframe.exists()).toBe(true)
    expect(iframe.attributes('src')).toContain('https://www.youtube.com/embed/abc123')
    expect(iframe.attributes('src')).toContain('autoplay=1')
    w.unmount()
  })

  it('renders no iframe when the trailer URL is not a safe https URL', () => {
    for (const url of ['javascript:alert(1)', 'http://insecure.test/x', '']) {
      const w = mountTrailer({ source: 'youtube', url })
      expect(w.find('iframe').exists()).toBe(false)
      w.unmount()
    }
  })
})

describe('DetailExtras — YouTube watch link', () => {
  it('encodes the video key in the href', () => {
    const w = mount(DetailExtras, {
      props: { media: { videos: [{ key: 'a b&z"', name: 'V', type: 'Trailer' }] } },
      global: { mocks: { $t: k => k } },
    })
    const link = w.find('a.vmd2-video-card')
    expect(link.exists()).toBe(true)
    expect(link.attributes('href')).toBe('https://www.youtube.com/watch?v=a%20b%26z%22')
    w.unmount()
  })
})
