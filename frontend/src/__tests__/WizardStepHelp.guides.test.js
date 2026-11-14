/**
 * First-login wizard, « Aides » step: « Autres guides », Help Center articles opened in
 * place, fetched once in the portal's language and rendered through the same scrub.
 */
import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createI18n } from 'vue-i18n'
import en from '@/locales/en.json'
import fr from '@/locales/fr.json'

const h = vi.hoisted(() => ({ apiGet: vi.fn() }))
vi.mock('@/composables/useApi', () => ({ useApi: () => ({ apiGet: h.apiGet }) }))

import HelpGuides from '@/components/portal/wizard/help/HelpGuides.vue'

const article = (slug, body) => ({ id: slug.length, slug, title: slug, body_html: body })
const CATALOGUE = {
  items: [
    article('les-quotas-de-demandes', '<p>Test quota body</p><img src="x" onerror="alert(1)">'),
    article('comment-gagner-de-l-xp', '<p>Test XP body</p><script>alert(1)</script>'),
    article('le-classement-mensuel', '<p>Test leaderboard body</p>'),
  ],
  lang: 'fr',
}

let wrapper

function mountGuides(locale = 'fr') {
  const i18n = createI18n({ legacy: false, locale, messages: { fr, en } })
  wrapper = mount(HelpGuides, {
    global: { plugins: [i18n], mocks: { $t: i18n.global.t } },
  })
  return wrapper
}

const rows = () => wrapper.findAll('.wzh-guide-btn')
const panel = () => wrapper.find('.wzh-guide-panel')

afterEach(() => {
  wrapper?.unmount()
  h.apiGet.mockReset()
})

describe('WizardStepHelp — other guides', () => {
  it('lists the four guides, closed, without asking the server yet', () => {
    mountGuides()
    expect(wrapper.find('h2').text()).toBe('Autres guides')
    expect(rows().map(row => row.text())).toEqual([
      'Les quotas de demandes',
      'Comment gagner de l’XP ?',
      'Le classement mensuel',
      'Le calendrier et la création d’événements',
    ])
    expect(rows().every(row => row.attributes('aria-expanded') === 'false')).toBe(true)
    expect(panel().exists()).toBe(false)
    expect(h.apiGet).not.toHaveBeenCalled()
  })

  it('opens an article under its row, scrubbed like in the Help Center', async () => {
    let answer
    h.apiGet.mockReturnValue(new Promise(resolve => (answer = resolve)))
    mountGuides()
    await rows()[0].trigger('click')
    expect(panel().text()).toBe('Chargement...')
    answer(CATALOGUE)
    await flushPromises()

    expect(h.apiGet).toHaveBeenCalledWith('/api/portal/help/articles?lang=fr')
    const row = rows()[0]
    expect(row.attributes('aria-expanded')).toBe('true')
    expect(panel().attributes('role')).toBe('region')
    expect(panel().attributes('id')).toBe(row.attributes('aria-controls'))
    expect(panel().attributes('aria-labelledby')).toBe(row.attributes('id'))
    const body = panel().find('.pt-help-article-body')
    expect(body.text()).toBe('Test quota body')
    expect(body.html()).not.toContain('onerror')

    await rows()[1].trigger('click')
    expect(wrapper.findAll('.wzh-guide-panel')).toHaveLength(1)
    expect(panel().text()).toBe('Test XP body')
    expect(panel().html()).not.toContain('<script')
    expect(h.apiGet).toHaveBeenCalledTimes(1)

    await rows()[1].trigger('click')
    expect(panel().exists()).toBe(false)
  })

  it('says so when a guide is missing from the Help Center', async () => {
    h.apiGet.mockResolvedValue(CATALOGUE)
    mountGuides()
    await rows()[3].trigger('click')
    await flushPromises()
    expect(panel().text()).toBe(
      'Ce guide n’est plus disponible. Retrouvez tous les guides dans le menu de votre avatar, rubrique Aide.',
    )
  })

  it('offers to try again when the articles cannot be loaded', async () => {
    h.apiGet.mockRejectedValueOnce(new Error('http_500')).mockResolvedValueOnce(CATALOGUE)
    mountGuides()
    await rows()[2].trigger('click')
    await flushPromises()
    expect(panel().text()).toContain('Le guide n’a pas pu être chargé.')

    await panel().find('.wzh-guide-retry').trigger('click')
    await flushPromises()
    expect(h.apiGet).toHaveBeenCalledTimes(2)
    expect(panel().text()).toBe('Test leaderboard body')
  })

  it('reads the articles in the portal language', async () => {
    h.apiGet.mockResolvedValue({ ...CATALOGUE, lang: 'en' })
    mountGuides('en')
    expect(rows()[1].text()).toBe('How do I earn XP?')
    await rows()[1].trigger('click')
    await flushPromises()
    expect(h.apiGet).toHaveBeenCalledWith('/api/portal/help/articles?lang=en')
  })
})
