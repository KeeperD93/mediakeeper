import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'

vi.mock('vue-i18n', () => ({
  useI18n: () => ({
    t: (key) => key,
  }),
}))

import PortalCreditsView from '@/views/portal/PortalCreditsView.vue'

const ImgStub = {
  inheritAttrs: false,
  template: '<img :src="$attrs.src" :alt="$attrs.alt" :data-test="$attrs[\'data-test\']" />',
}

const mountOpts = {
  global: {
    stubs: {
      'router-link': { template: '<a><slot /></a>' },
      img: ImgStub,
    },
  },
}

describe('PortalCreditsView', () => {
  it('renders the TMDB logo and the mandatory legal text without the unofficial-translation caveat', () => {
    const w = mount(PortalCreditsView, mountOpts)
    const logo = w.find('[data-test="pc-tmdb-logo"]')
    expect(logo.exists()).toBe(true)
    expect(logo.attributes('src')).toBe('/assets/icons/tmdb.svg')
    const legal = w.find('[data-test="pc-tmdb-legal"]')
    expect(legal.exists()).toBe(true)
    expect(legal.text()).toContain('TMDB API')
    expect(legal.text()).toContain('not endorsed or certified')
    expect(w.find('.pc-legal-note').exists()).toBe(false)
  })

  it('renders sections for the 5 third-party services', () => {
    const w = mount(PortalCreditsView, mountOpts)
    expect(w.find('[data-test="pc-tmdb"]').exists()).toBe(true)
    expect(w.find('[data-test="pc-opensubtitles"]').exists()).toBe(true)
    expect(w.find('[data-test="pc-emby"]').exists()).toBe(true)
    expect(w.find('[data-test="pc-imgur"]').exists()).toBe(true)
    expect(w.find('[data-test="pc-youtube"]').exists()).toBe(true)
  })

  it('renders the GitHub source code link in the footer', () => {
    const w = mount(PortalCreditsView, mountOpts)
    const footer = w.find('[data-test="pc-footer"]')
    expect(footer.exists()).toBe(true)
    const link = footer.find('a')
    expect(link.attributes('href')).toContain('github.com/KeeperD93/mediakeeper')
  })
})
