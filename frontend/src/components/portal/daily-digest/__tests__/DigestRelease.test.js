/**
 * The new Portal version in the daily digest: without news, a card that shows its first
 * changes; with news, a row heading their list. A click anywhere opens every change in
 * place, another one closes it, and only an opening tells the window.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { ref } from 'vue'

import { releaseView } from '@/utils/portal/dailyDigest'
import DigestCompactNews from '../DigestCompactNews.vue'
import DigestNews from '../DigestNews.vue'
import DigestRelease from '../DigestRelease.vue'

vi.mock('vue-i18n', async importOriginal => ({
  ...(await importOriginal()),
  useI18n: () => ({
    locale: ref('fr'),
    t: (key, params) =>
      params && typeof params === 'object' ? `${key}:${JSON.stringify(params)}` : key,
  }),
}))

const release = (extra = {}) => ({
  version: '1.2.3',
  date: '2026-11-13',
  is_new: true,
  categories: {
    Changed: ['Test change one', 'Test change two'],
    Fixed: ['Test fix one', 'Test fix two', 'Test fix three'],
    Security: ['Test unknown section'],
    Removed: [],
  },
  ...extra,
})

const news = id => ({
  id,
  title: `Test news ${id}`,
  content: 'First paragraph.',
  type: 'announcement',
  created_at: '2026-11-12T10:00:00Z',
  is_new: false,
})

let wrapper

describe('releaseView', () => {
  it('keeps the sections in order, the unknown one under its own name, the empty ones out', () => {
    const view = releaseView(release())

    expect(view.groups.map(group => [group.name, group.labelKey, group.count])).toEqual([
      ['Changed', 'changelog.cat.changed', '2'],
      ['Fixed', 'changelog.cat.fixed', '3'],
      ['Security', null, '1'],
    ])
    expect(view.groups[2].toneClass).toBe('')
    expect(view.total).toBe(6)
  })

  it('shows the first three changes and counts the others', () => {
    const view = releaseView(release())

    expect(view.teaser.map(change => [change.name, change.text])).toEqual([
      ['Changed', 'Test change one'],
      ['Changed', 'Test change two'],
      ['Fixed', 'Test fix one'],
    ])
    expect([view.rest, view.restLabel]).toEqual([3, '3'])
    expect(view.isNew).toBe(true)
    expect(view.date).toMatch(/13/)
  })
})

describe('DigestRelease.vue (card, no news)', () => {
  afterEach(() => wrapper?.unmount())

  it('shows the first changes, the others counted, and the « New » mark', () => {
    wrapper = mount(DigestRelease, { props: { release: release() } })

    expect(wrapper.findAll('.dd-release-teaser li')).toHaveLength(3)
    expect(wrapper.find('.dd-release-more').text()).toBe(
      'portal.dailyDigest.release.more:{"n":"3"}',
    )
    expect(wrapper.find('.dd-release-tag').text()).toBe('v1.2.3')
    expect(wrapper.find('.dd-release').classes()).toContain('dd-release--new')
    expect(wrapper.find('.dd-new-pill').exists()).toBe(true)
  })

  it('opens every change in place with one click and closes with another', async () => {
    wrapper = mount(DigestRelease, { props: { release: release() } })
    const button = wrapper.find('.dd-release-toggle')
    expect(button.attributes('aria-expanded')).toBe('false')
    expect(button.text()).toBe('portal.dailyDigest.release.showAll')

    await button.trigger('click')

    expect(wrapper.findAll('.dd-release-list li')).toHaveLength(6)
    expect(wrapper.find('.dd-release-teaser').exists()).toBe(false)
    expect(wrapper.find('.dd-release-more').exists()).toBe(false)
    expect(button.attributes('aria-expanded')).toBe('true')
    expect(button.attributes('aria-label')).toBe('portal.dailyDigest.release.collapse')
    expect(button.text()).toBe('')
    expect(wrapper.emitted('open')).toHaveLength(1)

    await button.trigger('click')

    expect(wrapper.find('.dd-release-list').exists()).toBe(false)
    expect(wrapper.findAll('.dd-release-teaser li')).toHaveLength(3)
    expect(wrapper.emitted('open')).toHaveLength(1)
  })

  it('wears no « New » mark once the version was opened', () => {
    wrapper = mount(DigestRelease, { props: { release: release({ is_new: false }) } })

    expect(wrapper.find('.dd-release').classes()).not.toContain('dd-release--new')
    expect(wrapper.find('.dd-new-pill').exists()).toBe(false)
  })

  it('sums the changes up in one line in the compact view', () => {
    wrapper = mount(DigestRelease, { props: { release: release(), compact: true } })

    expect(wrapper.find('.dd-release-summary').text()).toBe(
      'Test change one · Test change two · Test fix one',
    )
    expect(wrapper.find('.dd-release-toggle').text()).toBe(
      'portal.dailyDigest.release.showAllCompact:{"n":"6"}',
    )
    expect(wrapper.find('.dd-release-more').exists()).toBe(false)
  })
})

describe('the version row heading the news', () => {
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

  it('heads the list even under a single news item, and opens in place', async () => {
    wrapper = mount(DigestNews, { props: { news: [news(1)], release: release() } })
    const row = wrapper.find('.dd-more-item--release .dd-more-row')
    expect(row.find('.dd-more-title').text()).toBe(
      'portal.dailyDigest.release.line:{"version":"1.2.3","n":"6"}',
    )
    expect(row.find('.dd-new-mini').exists()).toBe(true)

    await row.trigger('click')

    expect(wrapper.findAll('.dd-more-item--release .dd-release-list li')).toHaveLength(6)
    expect(row.attributes('aria-expanded')).toBe('true')
    expect(wrapper.emitted('open-release')).toHaveLength(1)
    expect(wrapper.emitted('read')).toBeUndefined()

    await row.trigger('click')

    expect(wrapper.find('.dd-release-list').exists()).toBe(false)
  })

  it('shares « one open at a time » with the other news rows', async () => {
    wrapper = mount(DigestNews, { props: { news: [news(1), news(2)], release: release() } })
    const rows = wrapper.findAll('.dd-more-row')

    await rows[0].trigger('click')
    await rows[1].trigger('click')

    expect(wrapper.find('.dd-release-list').exists()).toBe(false)
    expect(wrapper.findAll('.dd-more-body')).toHaveLength(1)
    expect(wrapper.emitted('read')).toEqual([[2]])
  })

  it('heads the compact list too, and opens in place', async () => {
    wrapper = mount(DigestCompactNews, { props: { news: [news(1)], release: release() } })
    const row = wrapper.find('.dd-release-row .ddc-row-item')

    await row.trigger('click')

    expect(wrapper.findAll('.dd-release-row .dd-release-list li')).toHaveLength(6)
    expect(wrapper.emitted('open-release')).toHaveLength(1)

    await row.trigger('click')

    expect(wrapper.find('.ddc-rowbody').exists()).toBe(false)
  })

  it('leaves the list out when there is neither a version nor another item', () => {
    wrapper = mount(DigestNews, { props: { news: [news(1)] } })

    expect(wrapper.find('.dd-more-news').exists()).toBe(false)
  })
})
