import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'

vi.mock('vue-i18n', () => ({
  useI18n: () => ({
    t: key => key,
  }),
}))

import AdminAboutView from '@/views/AdminAboutView.vue'

describe('AdminAboutView', () => {
  it('renders the technical stack section with backend and frontend lines', () => {
    const w = mount(AdminAboutView, {
      global: { stubs: { 'router-link': { template: '<a><slot /></a>' } } },
    })
    const stack = w.find('[data-test="ab-stack"]')
    expect(stack.exists()).toBe(true)
    expect(stack.text()).toContain('Python 3.12')
    expect(stack.text()).toContain('FastAPI')
    expect(stack.text()).toContain('Vue 3')
    expect(stack.text()).not.toContain('Docker')
  })

  it('renders the FFmpeg LGPL license credit with the official legal URL', () => {
    const w = mount(AdminAboutView, {
      global: { stubs: { 'router-link': { template: '<a><slot /></a>' } } },
    })
    const ff = w.find('[data-test="ab-ffmpeg"]')
    expect(ff.exists()).toBe(true)
    const link = ff.find('a')
    expect(link.exists()).toBe(true)
    expect(link.attributes('href')).toBe('https://ffmpeg.org/legal.html')
  })

  it('links to the portal credits page for third-party API attributions', () => {
    const RouterLinkStub = {
      props: ['to'],
      template: '<a class="rl-stub" :data-target="JSON.stringify(to)"><slot /></a>',
    }
    const w = mount(AdminAboutView, {
      global: { stubs: { 'router-link': RouterLinkStub } },
    })
    const linkBlock = w.find('[data-test="ab-credits-link"]')
    expect(linkBlock.exists()).toBe(true)
    const rl = linkBlock.find('.rl-stub')
    expect(rl.exists()).toBe(true)
    expect(rl.attributes('data-target')).toContain('portal-credits')
  })
})
