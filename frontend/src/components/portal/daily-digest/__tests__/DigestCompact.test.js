/**
 * Daily digest, compact view: its sections in their order, none without data, the mini
 * top 3 with the viewer's row, and « Up next » bringing « For you » and events together.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mount, RouterLinkStub } from '@vue/test-utils'
import { ref } from 'vue'

import DigestCompact from '../DigestCompact.vue'

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

const digest = (extra = {}) => ({
  date: '2026-11-13',
  empty: false,
  me: { display_name: 'Alice', avatar_url: null, avatar_effect: 'meta', tier: 'gold' },
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

let wrapper
const render = data => {
  wrapper = mount(DigestCompact, {
    props: { digest: data },
    global: { stubs: { 'router-link': RouterLinkStub } },
  })
  return wrapper
}
const labels = () => wrapper.findAll('section').map(section => section.attributes('aria-label'))

describe('DigestCompact.vue', () => {
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

  it('keeps only the hello, the figures, the progress and the footer when there is nothing else', () => {
    render(digest())
    expect(labels()).toEqual([
      'portal.dailyDigest.aria.stats',
      'portal.dailyDigest.sections.progress',
    ])
    expect(wrapper.findAll('.ddc-stat-value').map(value => value.text())).toEqual(['0', '0'])
    expect(wrapper.find('.ddc-expiry').exists()).toBe(false)
    expect(wrapper.find('.ddc-split').exists()).toBe(false)
    expect(wrapper.find('.ddc-pi-top').exists()).toBe(false)
    expect(wrapper.find('.ddc-head .pt-avf-layer').classes()).toContain('gc-avatar-fx--meta')
  })

  it('shows every section it has data for, in the order of the design', () => {
    render(
      digest({
        expiry: { ends_at: '2026-11-14T00:00:00Z', days_left: 1 },
        news: [
          {
            id: 7,
            title: 'Test news',
            content: 'Hello.',
            image_url: null,
            type: 'announcement',
            pinned: false,
            created_at: '2026-11-12T10:00:00Z',
            is_new: true,
          },
        ],
        tickets_open: 1,
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
        events: [
          { id: 3, title: 'Test party', kind: 'private', scheduled_at: '2026-11-20T20:00:00Z' },
        ],
      }),
    )
    expect(wrapper.find('.ddc > .ddc-expiry').exists()).toBe(true)
    expect(labels()).toEqual([
      'portal.dailyDigest.sections.news',
      'portal.dailyDigest.aria.stats',
      'portal.dailyDigest.sections.progress',
      'portal.dailyDigest.sections.recentAdds',
      'portal.dailyDigest.sections.upNext',
    ])
    expect(wrapper.findAll('.ddc-stat-caption').map(caption => caption.text())).toEqual([
      'portal.dailyDigest.pills.streakCompact',
      'portal.dailyDigest.pills.ticketsCompact',
    ])
  })

  it('lists the top 3, a move or else the trophies, then the viewer', () => {
    render(
      digest({
        ranking: {
          position: 5,
          total: 12,
          movement: 2,
          top3: [
            entry(1, 'Bob', { trophies_won: 4 }),
            entry(2, 'Carol', { movement: 1, trophies_won: 2 }),
            entry(3, 'Dave', { movement: -1 }),
            entry(5, 'Alice', { is_current_user: true, movement: 2 }),
          ],
        },
      }),
    )
    const rows = wrapper.findAll('.ddc-lbrow')
    expect(rows.map(row => row.find('.ddc-lbpos').text())).toEqual(['1', '2', '3', '5'])
    expect(rows[0].find('.ddc-lbtr').text()).toBe('+4')
    expect(rows[1].find('.ddc-lbtr').exists()).toBe(false)
    expect(rows[1].find('.ddc-mv').text()).toBe('↑1')
    expect(rows[3].classes()).toContain('ddc-lbrow--me')
    expect(rows[3].find('.ddc-lb-pill').exists()).toBe(true)
  })

  it('brings « For you » and the events together in « Up next »', () => {
    render(
      digest({
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
            kind: 'ticket_reply',
            title: 'Test Movie',
            at: new Date(Date.now() - 2 * 3600e3).toISOString(),
            tmdb_id: null,
            media_type: null,
            ticket_id: 42,
          },
        ],
        events: [
          { id: 3, title: 'Test party', kind: 'public', scheduled_at: '2026-11-20T20:00:00Z' },
        ],
      }),
    )
    const rows = wrapper.findAll('.ddc-split .ddc-row')
    expect(rows.map(row => row.find('.ddc-row-title').text())).toEqual([
      'portal.dailyDigest.forYou.available:{"title":"Test Movie"}',
      'portal.dailyDigest.forYou.ticketReplyShort:{"title":"Test Movie"}',
      'Test party',
    ])
    expect(rows[0].find('.ddc-when').text()).toBe('portal.dailyDigest.forYou.see')
    expect(rows[1].find('.ddc-when').text()).toBe('2 h')
    const targets = wrapper.findAllComponents(RouterLinkStub).map(link => link.props('to'))
    expect(targets).toEqual(
      expect.arrayContaining([
        { name: 'portal-media-detail', params: { type: 'movie', id: 12345 } },
        { name: 'portal-ticket-detail', params: { id: 42 } },
        { name: 'portal-rooms', params: { id: 3 } },
      ]),
    )
  })
})
