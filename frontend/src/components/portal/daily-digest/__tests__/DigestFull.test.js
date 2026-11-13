/**
 * Daily digest, full view: its sections in their order, none without
 * data, the podium 2-1-3 with the viewer's row, and the lines that lead somewhere.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mount, RouterLinkStub } from '@vue/test-utils'
import { ref } from 'vue'

import DigestFull from '../DigestFull.vue'

vi.mock('vue-i18n', async importOriginal => ({
  ...(await importOriginal()),
  useI18n: () => ({
    locale: ref('fr'),
    t: (key, params) =>
      params && typeof params === 'object' ? `${key}:${JSON.stringify(params)}` : key,
  }),
}))

const entry = (rank, name, extra = {}) => ({
  rank,
  user_id: 1000 + rank,
  display_name: name,
  avatar_url: null,
  avatar_effect: null,
  level: 10,
  tier: 'gold',
  title_key: 'regular',
  period_xp: 900 - rank,
  movement: 0,
  trophies_won: 0,
  is_current_user: false,
  ...extra,
})

const base = (extra = {}) => ({
  date: '2026-11-13',
  empty: false,
  me: { display_name: 'Alice', avatar_url: null, avatar_effect: null, tier: 'gold' },
  level: {
    level: 12,
    xp: 340,
    xp_current_level: 300,
    xp_next_level: 500,
    xp_into_level: 40,
    percent: 68,
    maxed: false,
    title_key: 'regular',
    tier: 'gold',
    xp_yesterday: 0,
  },
  recent_adds: [],
  events: [],
  ranking: { position: 0, total: 0, movement: 0, top3: [] },
  quota: { used: 0, max_allowed: 0, unlimited: true, remaining: -1 },
  tickets_open: 0,
  streak: 0,
  next_achievement: null,
  expiry: null,
  news: [],
  for_you: [],
  ...extra,
})

const full = () =>
  base({
    expiry: { ends_at: '2026-12-12T00:00:00Z', days_left: 29 },
    news: [
      {
        id: 7,
        title: 'Test news',
        content: 'Hello.',
        image_url: null,
        type: 'announcement',
        pinned: true,
        created_at: '2026-11-12T10:00:00Z',
        is_new: false,
      },
    ],
    streak: 6,
    ranking: {
      position: 5,
      total: 12,
      movement: 2,
      top3: [
        entry(1, 'Bob'),
        entry(2, 'Carol', { movement: 1, trophies_won: 2 }),
        entry(3, 'Dave', { movement: -1 }),
        entry(5, 'Alice', { is_current_user: true, movement: 2 }),
      ],
    },
    next_achievement: {
      id: 'night_owl',
      name_key: 'achievements.test.name',
      description_key: 'achievements.test.desc',
      icon: 'moon',
      tier: 1,
      progress: 8,
      threshold: 10,
      remaining: 2,
    },
    recent_adds: [
      {
        tmdb_id: 12345,
        emby_item_id: 'e1',
        title: 'Test Movie',
        year: '2024',
        media_type: 'movie',
        poster_url: null,
        date_created: '2026-11-12',
      },
    ],
    for_you: [
      {
        kind: 'request_available',
        title: 'Test Movie',
        at: '2026-11-13T08:00:00Z',
        tmdb_id: 12345,
        media_type: 'movie',
        ticket_id: null,
      },
      {
        kind: 'request_approved',
        title: 'Test Show',
        at: '2026-11-13T07:00:00Z',
        tmdb_id: 678,
        media_type: 'tv',
        ticket_id: null,
      },
      {
        kind: 'ticket_reply',
        title: 'Test Movie',
        at: '2026-11-13T06:00:00Z',
        tmdb_id: null,
        media_type: null,
        ticket_id: 42,
      },
    ],
    events: [{ id: 3, title: 'Test party', kind: 'public', scheduled_at: '2026-11-20T20:00:00Z' }],
  })

let wrapper
const render = digest => {
  wrapper = mount(DigestFull, {
    props: { digest },
    global: { stubs: { 'router-link': RouterLinkStub } },
  })
  return wrapper
}

describe('DigestFull.vue', () => {
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

  it('shows every section it has data for, in the order of the design', () => {
    render(full())
    const children = wrapper.find('.dd-full').element.children
    expect(children[0].classList).toContain('dd-hero')
    expect(children[1].classList).toContain('dd-expiry')
    expect(wrapper.findAll('section').map(section => section.attributes('aria-label'))).toEqual([
      'portal.dailyDigest.sections.news',
      'portal.dailyDigest.aria.stats',
      'portal.dailyDigest.sections.progress',
      'portal.dailyDigest.sections.recentAdds',
      'portal.dailyDigest.sections.forYou',
      'portal.dailyDigest.sections.events',
    ])
    expect(wrapper.find('.dd-ach').exists()).toBe(true)
    expect(wrapper.find('.dd-top3').exists()).toBe(true)
    expect(children[children.length - 1].tagName).toBe('FOOTER')
  })

  it('leaves out every section it has nothing for', () => {
    render(base())
    expect(wrapper.findAll('section').map(section => section.attributes('aria-label'))).toEqual([
      'portal.dailyDigest.aria.stats',
      'portal.dailyDigest.sections.progress',
    ])
    expect(wrapper.find('.dd-expiry').exists()).toBe(false)
    expect(wrapper.find('.dd-ach').exists()).toBe(false)
    expect(wrapper.find('.dd-top3').exists()).toBe(false)
  })

  it('shows the streak and the open tickets at 0 rather than leaving a hole', () => {
    render(base())
    const cards = wrapper.findAll('.dd-stat')
    expect(cards.map(card => card.find('.dd-stat-label').text())).toEqual([
      'portal.dailyDigest.pills.streak',
      'portal.dailyDigest.pills.tickets',
    ])
    expect(cards.map(card => card.find('.dd-stat-value').text())).toEqual(['0', '0'])
    expect(cards[1].find('.dd-stat-caption').text()).toBe(
      'portal.dailyDigest.pills.ticketsCaptionNone',
    )
  })

  it('greets the viewer by their public name', () => {
    render(base())
    expect(wrapper.find('.dd-hello').text()).toMatch(/WithName:\{"name":"Alice"\}$/)
  })

  it('shows yesterday’s XP only when some was earned', () => {
    render(base())
    expect(wrapper.find('.dd-xpchip').exists()).toBe(false)
    wrapper.unmount()

    const digest = base()
    digest.level.xp_yesterday = 45
    render(digest)
    expect(wrapper.find('.dd-xpchip').text()).toBe(
      'portal.dailyDigest.level.xpYesterday:{"n":"45"}',
    )
  })

  it('stands the top 3 on a podium 2-1-3, then the viewer further down', () => {
    render(full())
    const cards = wrapper.findAll('.dd-pcard')
    expect(cards.map(card => card.find('.dd-pname').text())).toEqual(['Bob', 'Carol', 'Dave'])
    expect(cards.map(card => card.classes().find(name => name.startsWith('dd-pcard--')))).toEqual([
      'dd-pcard--1',
      'dd-pcard--2',
      'dd-pcard--3',
    ])
    expect(cards.map(card => card.classes().find(name => name.startsWith('lb-metal--')))).toEqual([
      'lb-metal--gold',
      'lb-metal--silver',
      'lb-metal--bronze',
    ])
    expect(cards[1].find('.dd-trophies').text()).toBe('+2')
    expect(cards[1].find('.dd-mv').text()).toBe('↑1')
    expect(cards[2].find('.dd-mv').classes()).toContain('dd-mv--down')
    expect(wrapper.find('.dd-me .dd-me-n').text()).toBe('Alice')
    expect(wrapper.find('.dd-me .dd-me-pos').text()).toBe('5')
  })

  it('leads each podium card to its profile, and the link to the ranking page', () => {
    render(full())
    const targets = wrapper.findAllComponents(RouterLinkStub).map(link => link.props('to'))
    expect(targets).toEqual(
      expect.arrayContaining([
        { name: 'portal-user-profile', params: { id: 1001 } },
        { name: 'portal-leaderboard' },
      ]),
    )
  })

  it('shows no viewer row when the viewer is on the podium', () => {
    const digest = full()
    digest.ranking.top3 = [entry(1, 'Alice', { is_current_user: true }), entry(2, 'Bob')]
    render(digest)
    expect(wrapper.findAll('.dd-pcard')).toHaveLength(2)
    expect(wrapper.find('.dd-me').exists()).toBe(false)
  })

  it('links an available request to its page and a reply to its ticket, not an approval', () => {
    render(full())
    const rows = wrapper.findAll('.dd-fy-row')
    expect(rows).toHaveLength(3)
    expect(rows[0].findComponent(RouterLinkStub).props('to')).toEqual({
      name: 'portal-media-detail',
      params: { type: 'movie', id: 12345 },
    })
    expect(rows[1].findComponent(RouterLinkStub).exists()).toBe(false)
    expect(rows[1].find('.dd-fy-s').text()).toBe('portal.dailyDigest.forYou.approvedHint')
    expect(rows[2].findComponent(RouterLinkStub).props('to')).toEqual({
      name: 'portal-ticket-detail',
      params: { id: 42 },
    })
  })

  it('leads an event to its room and leaves the window', async () => {
    render(full())
    const link = wrapper.findAllComponents(RouterLinkStub).find(item => item.classes('dd-ev'))
    expect(link.props('to')).toEqual({ name: 'portal-rooms', params: { id: 3 } })

    await link.trigger('click')
    expect(wrapper.emitted('leave')).toHaveLength(1)
  })

  it('writes the expiry with its date and its delay', () => {
    render(full())
    expect(wrapper.find('.dd-expiry-t').text()).toContain('portal.dailyDigest.expiry.title')
    expect(wrapper.find('.dd-expiry-t').text()).toContain('portal.dailyDigest.expiry.when')
  })
})
