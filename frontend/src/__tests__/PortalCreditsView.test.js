/**
 * Portal Credits page, read with the real texts: the OpenSubtitles sentence
 * holds its link in place, so the full stop follows it directly.
 */
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { createI18n } from 'vue-i18n'
import en from '@/locales/en.json'
import fr from '@/locales/fr.json'

import PortalCreditsView from '@/views/portal/PortalCreditsView.vue'
import pkg from '../../package.json'

const ImgStub = {
  inheritAttrs: false,
  template: '<img :src="$attrs.src" :alt="$attrs.alt" :data-test="$attrs[\'data-test\']" />',
}

function mountCredits(locale = 'fr') {
  const i18n = createI18n({ legacy: false, locale, messages: { fr, en } })
  return mount(PortalCreditsView, {
    global: {
      plugins: [i18n],
      stubs: { 'router-link': { template: '<a><slot /></a>' }, img: ImgStub },
    },
  })
}

describe('PortalCreditsView', () => {
  it('renders the TMDB logo and the mandatory legal text without the unofficial-translation caveat', () => {
    const w = mountCredits()
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
    const w = mountCredits()
    expect(w.find('[data-test="pc-tmdb"]').exists()).toBe(true)
    expect(w.find('[data-test="pc-opensubtitles"]').exists()).toBe(true)
    expect(w.find('[data-test="pc-emby"]').exists()).toBe(true)
    expect(w.find('[data-test="pc-imgur"]').exists()).toBe(true)
    expect(w.find('[data-test="pc-youtube"]').exists()).toBe(true)
  })

  it('renders the GitHub source code link in the footer', () => {
    const footer = mountCredits().find('[data-test="pc-footer"]')
    expect(footer.exists()).toBe(true)
    expect(footer.find('a').attributes('href')).toContain('github.com/KeeperD93/mediakeeper')
  })

  it('shows the app version from package.json in the footer', () => {
    const footer = mountCredits().find('[data-test="pc-footer"]')
    expect(pkg.version).toBeTruthy()
    expect(footer.text()).toContain(`MediaKeeper v${pkg.version}`)
  })

  it.each([
    ['fr', 'Sous-titres fournis par OpenSubtitles. Visitez opensubtitles.org.'],
    ['en', 'Subtitles powered by OpenSubtitles. Visit opensubtitles.org.'],
  ])('ends the %s OpenSubtitles sentence right after its link', (locale, shown) => {
    const sentence = mountCredits(locale).find('[data-test="pc-opensubtitles"] p')
    expect(sentence.text()).toBe(shown)
    // The link text itself carries no padding space either.
    const link = sentence.find('a')
    expect(link.element.textContent).toBe('opensubtitles.org')
    expect(link.attributes('href')).toBe('https://www.opensubtitles.org')
  })
})
