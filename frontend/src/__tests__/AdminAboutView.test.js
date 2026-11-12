/**
 * About page, read with the real texts: each sentence holds its link in place,
 * so the full stop follows the link directly ("GitHub.", never "GitHub .").
 */
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { createI18n } from 'vue-i18n'
import en from '@/locales/en.json'
import fr from '@/locales/fr.json'

import AdminAboutView from '@/views/AdminAboutView.vue'

const RouterLinkStub = {
  props: ['to'],
  template: '<a class="rl-stub" :data-target="JSON.stringify(to)"><slot /></a>',
}

function mountAbout(locale = 'fr') {
  const i18n = createI18n({ legacy: false, locale, messages: { fr, en } })
  return mount(AdminAboutView, {
    global: { plugins: [i18n], stubs: { 'router-link': RouterLinkStub } },
  })
}

describe('AdminAboutView', () => {
  it('renders the technical stack section with backend and frontend lines', () => {
    const stack = mountAbout().find('[data-test="ab-stack"]')
    expect(stack.exists()).toBe(true)
    expect(stack.text()).toContain('Python 3.14')
    expect(stack.text()).toContain('FastAPI')
    expect(stack.text()).toContain('Vue 3')
    expect(stack.text()).not.toContain('Docker')
  })

  it.each([
    ['fr', ['Backend :', 'Frontend :']],
    ['en', ['Backend:', 'Frontend:']],
  ])('leaves the colon after each stack label to the %s translation', (locale, shown) => {
    const labels = mountAbout(locale)
      .findAll('[data-test="ab-stack"] strong')
      .map(label => label.text())
    expect(labels).toEqual(shown)
  })

  it('renders the FFmpeg LGPL license credit with the official legal URL', () => {
    const link = mountAbout().find('[data-test="ab-ffmpeg"] a')
    expect(link.exists()).toBe(true)
    expect(link.attributes('href')).toBe('https://ffmpeg.org/legal.html')
  })

  it('links to the portal credits page for third-party API attributions', () => {
    const rl = mountAbout().find('[data-test="ab-credits-link"] .rl-stub')
    expect(rl.exists()).toBe(true)
    expect(rl.attributes('data-target')).toContain('portal-credits')
  })

  it.each([
    [
      'fr',
      'MediaKeeper utilise des outils du projet FFmpeg sous licence LGPLv2.1+. Voir ffmpeg.org/legal.html.',
      "Voir requirements.txt et package.json pour l'arborescence complète des dépendances open-source sur GitHub.",
      'Les attributions visibles pour TMDB, OpenSubtitles, Emby, Imgur et YouTube sont listées sur /portal/credits.',
    ],
    [
      'en',
      'MediaKeeper uses tools from the FFmpeg project under the LGPLv2.1+ license. See ffmpeg.org/legal.html.',
      'See requirements.txt and package.json for the full open-source dependency tree on GitHub.',
      'User-facing attributions for TMDB, OpenSubtitles, Emby, Imgur and YouTube are listed on /portal/credits.',
    ],
  ])('ends each %s sentence right after its link', (locale, ffmpeg, dependencies, credits) => {
    const w = mountAbout(locale)
    const para = sel => w.find(`[data-test="${sel}"]`)
    expect(para('ab-ffmpeg').text()).toBe(ffmpeg)
    expect(para('ab-dependencies').text()).toBe(dependencies)
    expect(para('ab-credits-link').find('p').text()).toBe(credits)
    // The link text itself carries no padding space either.
    expect(para('ab-dependencies').find('a').element.textContent).toBe('GitHub')
  })
})
