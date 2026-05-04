import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'

vi.mock('vue-i18n', () => ({
  useI18n: () => ({
    t: key => key,
  }),
}))

import AttributionFooter from '@/components/common/AttributionFooter.vue'

const ImgStub = {
  inheritAttrs: false,
  template: '<img :src="$attrs.src" :alt="$attrs.alt" :class="$attrs.class" />',
}

describe('AttributionFooter', () => {
  it('preserves the TMDB logo link required by TMDB attribution policy', () => {
    const w = mount(AttributionFooter, {
      global: {
        stubs: {
          'router-link': { template: '<a><slot /></a>' },
          img: ImgStub,
        },
      },
    })
    const logo = w.find('img.mk-attribution-logo')
    expect(logo.exists()).toBe(true)
    expect(logo.attributes('src')).toBe('/assets/icons/tmdb.svg')
  })

  it('renders a router-link towards the portal-credits route', () => {
    const RouterLinkStub = {
      props: ['to'],
      template: '<a class="rl-stub" :data-target="JSON.stringify(to)"><slot /></a>',
    }
    const w = mount(AttributionFooter, {
      global: {
        stubs: {
          'router-link': RouterLinkStub,
          img: ImgStub,
        },
      },
    })
    const link = w.find('.mk-attribution-credits')
    expect(link.exists()).toBe(true)
    expect(link.attributes('data-target')).toContain('portal-credits')
    expect(link.text()).toContain('attribution.footer.fullCredits')
  })
})
