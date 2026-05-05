import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'

vi.mock('vue-i18n', () => ({
  useI18n: () => ({
    t: (key, params) => (params ? `${key}:${JSON.stringify(params)}` : key),
  }),
}))

import TicketCard from '@/components/portal/tickets/TicketCard.vue'

const MOVIE_TICKET = {
  id: 7,
  media_type: 'movie',
  media_title: 'Interstellar',
  emby_item_id: 'emby-mov-1',
  series_emby_id: null,
  selected_seasons: null,
  status: 'open',
  priority: 'minor',
  issue_type: 'audio',
  created_at: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
  replies_count: 0,
}

describe('TicketCard', () => {
  it('renders the Emby poster for a library ticket', () => {
    const w = mount(TicketCard, { props: { ticket: MOVIE_TICKET } })
    expect(w.find('.tcd-poster').exists()).toBe(true)
    expect(w.find('.tcd-poster').attributes('src')).toContain('/api/emby/image/emby-mov-1')
    expect(w.find('.tcd-visual--icon').exists()).toBe(false)
  })

  it('renders an issue icon visual for "other" tickets (no Emby anchor)', () => {
    const w = mount(TicketCard, {
      props: {
        ticket: {
          ...MOVIE_TICKET,
          media_type: 'other',
          emby_item_id: null,
          issue_type: 'metadata',
        },
      },
    })
    expect(w.find('.tcd-poster').exists()).toBe(false)
    expect(w.find('.tcd-visual--icon').exists()).toBe(true)
  })

  it('renders the status pill matching the ticket status', () => {
    const w = mount(TicketCard, {
      props: { ticket: { ...MOVIE_TICKET, status: 'in_progress' } },
    })
    expect(w.find('.tcd-pill--status-in_progress').exists()).toBe(true)
    expect(w.classes()).toContain('tcd--status-in_progress')
  })

  it('shows the blocking pill only when priority is blocking', () => {
    const minor = mount(TicketCard, { props: { ticket: MOVIE_TICKET } })
    expect(minor.find('.tcd-pill--blocking').exists()).toBe(false)

    const blocking = mount(TicketCard, {
      props: { ticket: { ...MOVIE_TICKET, priority: 'blocking' } },
    })
    expect(blocking.find('.tcd-pill--blocking').exists()).toBe(true)
  })

  it('renders the scope label for an episode-targeted series ticket', () => {
    const ticket = {
      ...MOVIE_TICKET,
      media_type: 'episode',
      series_emby_id: 'emby-ser-42',
      emby_item_id: null,
      selected_seasons: [{ season_number: 2, episodes: [1, 3] }],
    }
    const w = mount(TicketCard, { props: { ticket } })
    expect(w.find('.tcd-scope').text()).toContain('portal.tickets.detail.scope.episodes')
    expect(w.find('.tcd-scope').text()).toContain('1, 3')
  })

  it('hides the scope label for "whole series" tickets', () => {
    const ticket = { ...MOVIE_TICKET, media_type: 'series', selected_seasons: null }
    const w = mount(TicketCard, { props: { ticket } })
    expect(w.find('.tcd-scope').exists()).toBe(false)
  })

  it('emits "open" with the ticket id on click', async () => {
    const w = mount(TicketCard, { props: { ticket: MOVIE_TICKET } })
    await w.trigger('click')
    expect(w.emitted('open')[0]).toEqual([7])
  })

  it('emits "open" on Enter key for keyboard users', async () => {
    const w = mount(TicketCard, { props: { ticket: MOVIE_TICKET } })
    await w.trigger('keydown', { key: 'Enter' })
    expect(w.emitted('open')[0]).toEqual([7])
  })
})
