/**
 * Running XP boosts in the daily digest: a green row of the news list between the
 * version and the events (« Reduced XP » in orange under ×1), opened in place on its
 * text, the actions that count and the time left; alone after the version without news.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mount, RouterLinkStub } from '@vue/test-utils'
import { ref } from 'vue'

import { localizedNumber } from '@/utils/localizedNumber'
import { boostView, timeLeft } from '@/utils/portal/dailyDigest'
import DigestBoosts from '../DigestBoosts.vue'
import DigestCompact from '../DigestCompact.vue'
import DigestCompactNews from '../DigestCompactNews.vue'
import DigestFull from '../DigestFull.vue'
import DigestNews from '../DigestNews.vue'

vi.mock('vue-i18n', async importOriginal => ({
  ...(await importOriginal()),
  useI18n: () => ({
    locale: ref('en'),
    t: (key, params) =>
      params && typeof params === 'object' ? `${key}:${JSON.stringify(params)}` : key,
  }),
}))

const MINUTE = 60_000
const HOUR = 60 * MINUTE
const DAY = 24 * HOUR
const NOW = Date.parse('2026-11-15T12:00:00Z')
const K = 'portal.dailyDigest.boost'

const boost = (id, extra = {}) => ({
  id,
  name: `Test Boost ${id}`,
  description: 'First paragraph.\n\nSecond paragraph.',
  multiplier: 1.5,
  ends_at: new Date(Date.now() + 51 * DAY + HOUR).toISOString(),
  ends_local: '2027-01-03T23:59:00',
  actions: [],
  ...extra,
})

const news = (id, extra = {}) => ({
  id,
  title: `Test news ${id}`,
  content: 'First paragraph.',
  type: 'announcement',
  created_at: '2026-11-12T10:00:00Z',
  is_new: false,
  ...extra,
})

const release = { version: '1.2.3', date: '2026-11-13', is_new: false, categories: {} }

let wrapper

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

describe('timeLeft and boostView', () => {
  it.each([
    [51 * DAY + 5 * HOUR, { unit: 'days', n: 51 }],
    [DAY, { unit: 'days', n: 1 }],
    [5 * HOUR + 59 * MINUTE, { unit: 'hours', n: 5 }],
    [20 * MINUTE + 30_000, { unit: 'minutes', n: 20 }],
    [10_000, { unit: 'minutes', n: 1 }],
    [-HOUR, { unit: 'minutes', n: 1 }],
  ])('counts %i ms left in its largest whole unit', (ms, expected) => {
    expect(timeLeft(new Date(NOW + ms).toISOString(), NOW)).toEqual(expected)
  })

  it('draws a boost: under ×1 it is reduced, its actions get a name to look up', () => {
    const view = boostView(
      boost(4, {
        multiplier: 0.5,
        ends_at: new Date(NOW + 3 * HOUR).toISOString(),
        actions: ['watch_movie'],
      }),
      NOW,
    )

    expect(view).toMatchObject({
      key: 'boost-4',
      name: 'Test Boost 4',
      reduced: true,
      leftKey: `${K}.left.hours`,
      left: 3,
      paragraphs: ['First paragraph.', 'Second paragraph.'],
      actions: [{ key: `${K}.actions.watch_movie`, action: 'watch_movie' }],
    })
    expect(boostView(boost(5, { multiplier: 1 }), NOW).reduced).toBe(false)
  })

  it("shows the end on the server's clock, whatever the browser's zone", () => {
    // A server in New York: 23:59 there is 04:59 the next day in UTC.
    const view = boostView(boost(6, { ends_at: '2027-01-04T04:59:00Z' }), NOW)

    expect(view.ends).toMatch(/(11|23):59/)
    expect(view.ends).toMatch(/3/)
    expect(view.until).toMatch(/3/)
    expect(view.until).not.toMatch(/4/)
  })
})

describe('the boost row in the news list', () => {
  const rowNames = () =>
    wrapper.findAll('.dd-more-item').map(item => {
      if (item.classes('dd-more-item--release')) return 'release'
      if (item.classes('dd-more-item--boost')) return 'boost'
      return item.find('.dd-more-title').text()
    })

  it('comes after the version and before the events, one row per boost', () => {
    wrapper = mount(DigestNews, {
      props: {
        news: [news(3, { type: 'event' }), news(2, { type: 'maintenance' }), news(1)],
        release,
        boosts: [boost(1), boost(2)],
      },
    })

    expect(rowNames()).toEqual(['Test news 2', 'release', 'boost', 'boost', 'Test news 3'])
    const row = wrapper.find('.dd-more-item--boost')
    expect(row.classes()).toContain('dd-boost--up')
    expect(row.find('.dd-badge').classes()).toContain('dd-badge--boost')
    expect(row.find('.dd-badge').text()).toBe(`${K}.badge`)
    expect(row.find('.dd-more-title').text()).toBe(
      `${K}.line:${JSON.stringify({ name: 'Test Boost 1', multiplier: localizedNumber(1.5) })}`,
    )
    expect(row.find('.dd-more-date').text()).toMatch(new RegExp(`^${K}.until:`))
    expect(row.find('.dd-new-mini').exists()).toBe(false)
  })

  it('opens in place on its text, the actions that count and the time left', async () => {
    wrapper = mount(DigestNews, {
      props: {
        news: [news(1), news(2)],
        boosts: [boost(1, { actions: ['watch_movie', 'watch_episode'] })],
      },
    })
    const button = wrapper.find('.dd-more-item--boost .dd-more-row')

    await button.trigger('click')

    const lines = wrapper.findAll('.dd-more-item--boost .dd-more-body p').map(p => p.text())
    expect(lines.slice(0, 2)).toEqual(['First paragraph.', 'Second paragraph.'])
    expect(lines[2]).toBe(
      `${K}.counts:{"actions":"${K}.actions.watch_movie and ${K}.actions.watch_episode"}`,
    )
    const [, ends] = lines[3].split(`${K}.ends:`)
    expect(JSON.parse(ends).left).toBe(`${K}.left.days:{"n":"51"}`)
    expect(wrapper.find('.dd-boost-end').text()).toBe(lines[3])
    expect(button.attributes('aria-expanded')).toBe('true')
    expect(wrapper.find('.dd-more-item--boost').classes()).toContain('dd-more-item--open')
    expect(wrapper.emitted('read')).toBeUndefined()
    expect(wrapper.emitted('open-release')).toBeUndefined()

    // One row open at a time: another one closes it.
    await wrapper.findAll('.dd-more-row')[0].trigger('click')
    expect(wrapper.find('.dd-more-item--boost .dd-more-body').exists()).toBe(false)
  })

  it('says nothing of actions when every action counts', async () => {
    wrapper = mount(DigestNews, { props: { news: [news(1)], boosts: [boost(1)] } })

    await wrapper.find('.dd-more-item--boost .dd-more-row').trigger('click')

    expect(wrapper.findAll('.dd-more-item--boost .dd-more-body p')).toHaveLength(3)
    expect(wrapper.text()).not.toContain(`${K}.counts`)
  })

  it('turns orange as « Reduced XP » under ×1', () => {
    wrapper = mount(DigestNews, {
      props: { news: [news(1)], boosts: [boost(1, { multiplier: 0.5 })] },
    })
    const row = wrapper.find('.dd-more-item--boost')

    expect(row.classes()).toContain('dd-boost--down')
    expect(row.find('.dd-badge').classes()).toContain('dd-badge--warn')
    expect(row.find('.dd-badge').text()).toBe(`${K}.badgeReduced`)
  })

  it('stays in sight in the compact list, read news behind « +N », and opens in place', async () => {
    wrapper = mount(DigestCompactNews, {
      props: { news: [news(1), news(2, { type: 'event' })], boosts: [boost(1)] },
    })
    const row = wrapper.find('.dd-boost-row .ddc-row-item')
    expect(wrapper.findAll('.ddc-row-item')).toHaveLength(1)
    expect(row.find('.dd-chev').exists()).toBe(false)

    await row.trigger('click')

    expect(wrapper.findAll('.dd-boost-row .ddc-rowbody p')).toHaveLength(3)
    expect(row.attributes('aria-expanded')).toBe('true')
    expect(wrapper.emitted('read')).toBeUndefined()
  })
})

describe('the boosts without news', () => {
  it('open one at a time in their own list', async () => {
    wrapper = mount(DigestBoosts, { props: { boosts: [boost(1), boost(2)] } })
    const buttons = wrapper.findAll('.dd-more-row')
    expect(wrapper.find('section').classes()).toContain('dd-boost-list')
    expect(wrapper.find('section').attributes('aria-label')).toBe(`${K}.section`)

    await buttons[0].trigger('click')
    await buttons[1].trigger('click')

    expect(wrapper.findAll('.dd-more-body')).toHaveLength(1)
    expect(buttons.map(button => button.attributes('aria-expanded'))).toEqual(['false', 'true'])
  })

  const digest = extra => ({
    date: '2026-11-13',
    empty: false,
    me: { display_name: 'Alice', avatar_url: null, avatar_effect: null, tier: null },
    news: [],
    release,
    xp_boosts: [boost(1)],
    ...extra,
  })
  const mountView = (view, extra = {}) => {
    wrapper = mount(view, {
      props: { digest: digest(extra) },
      global: { stubs: { 'router-link': RouterLinkStub } },
    })
  }
  const after = (first, second) =>
    !!(first.element.compareDocumentPosition(second.element) & Node.DOCUMENT_POSITION_FOLLOWING)

  it('come alone after the version in the full view', () => {
    mountView(DigestFull)

    expect(after(wrapper.find('.dd-release'), wrapper.find('.dd-boost-list'))).toBe(true)
    expect(wrapper.find('.dd-boost-list .dd-more-item--boost').exists()).toBe(true)
  })

  it('come alone after the version in the compact view', () => {
    mountView(DigestCompact)

    const box = wrapper.find('section.ddc-box')
    expect(after(wrapper.find('.dd-release'), box)).toBe(true)
    expect(box.find('.dd-boost-row').exists()).toBe(true)
  })

  it('join the news list when there is news', () => {
    mountView(DigestFull, { news: [news(1)] })

    expect(wrapper.find('.dd-boost-list').exists()).toBe(false)
    expect(wrapper.find('.dd-more-news .dd-more-item--boost').exists()).toBe(true)
  })

  it('leave no trace when none is running', () => {
    mountView(DigestCompact, { xp_boosts: [] })

    expect(wrapper.find('.dd-boost-row').exists()).toBe(false)
    expect(wrapper.find('section.ddc-box').exists()).toBe(false)
  })
})
