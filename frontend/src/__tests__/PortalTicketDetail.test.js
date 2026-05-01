import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'

const currentTicket = ref(null)
const profileRef = ref({ role: 'viewer' })

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { id: '1' } }),
}))

vi.mock('vue-i18n', () => ({
  useI18n: () => ({
    t: (key, params) => (params ? `${key}:${JSON.stringify(params)}` : key),
  }),
}))

vi.mock('@/composables/portal/usePortalTickets', () => ({
  usePortalTickets: () => ({
    currentTicket,
    fetchTicket: vi.fn(),
    replyTicket: vi.fn(),
    updateStatus: vi.fn(),
  }),
}))

vi.mock('@/composables/portal/usePortalAuth', () => ({
  usePortalAuth: () => ({ profile: profileRef }),
}))

vi.mock('@/composables/useToast', () => ({
  useToast: () => ({ showToast: vi.fn() }),
}))

// The thread is covered by its own test — stub it here to keep the
// detail-view checks focused on hero/header/toolbar concerns.
vi.mock('@/components/portal/tickets/TicketThread.vue', () => ({
  default: {
    name: 'TicketThread',
    props: ['ticket'],
    template: '<div class="tth-stub" />',
  },
}))

import PortalTicketDetail from '@/views/portal/PortalTicketDetail.vue'

function setTicket(payload) {
  currentTicket.value = {
    id: 1,
    user_id: 17,
    media_type: 'movie',
    media_title: 'Interstellar',
    issue_type: 'audio',
    priority: 'minor',
    status: 'open',
    description: 'Audio désynchro',
    created_at: '2026-04-28T10:00:00Z',
    updated_at: '2026-04-28T10:00:00Z',
    replies: [],
    emby_item_id: 'emby-mov-1',
    series_emby_id: null,
    selected_seasons: null,
    ...payload,
  }
}

describe('PortalTicketDetail', () => {
  beforeEach(() => {
    profileRef.value = { role: 'viewer' }
    currentTicket.value = null
  })

  it('renders the hero with poster + title for a library ticket', async () => {
    setTicket({})
    const w = mount(PortalTicketDetail)
    await flushPromises()
    expect(w.find('.ptd-hero').exists()).toBe(true)
    expect(w.find('.ptd-hero-poster').attributes('src')).toContain('/api/emby/image/emby-mov-1')
    expect(w.text()).toContain('Interstellar')
  })

  it('uses the compact header for "other" tickets — no hero', async () => {
    setTicket({
      media_type: 'other',
      media_title: 'Bug application',
      emby_item_id: null,
      series_emby_id: null,
    })
    const w = mount(PortalTicketDetail)
    await flushPromises()
    expect(w.find('.ptd-hero').exists()).toBe(false)
    expect(w.find('.ptd-other-header').exists()).toBe(true)
    expect(w.text()).toContain('Bug application')
  })

  it('renders the scope label for a season-targeted series ticket', async () => {
    setTicket({
      media_type: 'season',
      media_title: 'Severance',
      emby_item_id: null,
      series_emby_id: 'emby-ser-42',
      selected_seasons: [{ season_number: 2 }],
    })
    const w = mount(PortalTicketDetail)
    await flushPromises()
    expect(w.find('.ptd-hero-scope').text()).toContain('portal.tickets.detail.scope.season')
  })

  it('renders the episodes scope label for episode-targeted tickets', async () => {
    setTicket({
      media_type: 'episode',
      media_title: 'Severance',
      emby_item_id: null,
      series_emby_id: 'emby-ser-42',
      selected_seasons: [{ season_number: 1, episodes: [1, 3, 5] }],
    })
    const w = mount(PortalTicketDetail)
    await flushPromises()
    expect(w.find('.ptd-hero-scope').text()).toContain('portal.tickets.detail.scope.episodes')
    expect(w.find('.ptd-hero-scope').text()).toContain('1, 3, 5')
  })

  it('hides the admin status control for non-admin users', async () => {
    setTicket({})
    const w = mount(PortalTicketDetail)
    await flushPromises()
    expect(w.find('.ptd-status-control').exists()).toBe(false)
  })

  it('shows the admin status control when the profile is admin', async () => {
    profileRef.value = { role: 'admin' }
    setTicket({})
    const w = mount(PortalTicketDetail)
    await flushPromises()
    expect(w.find('.ptd-status-control').exists()).toBe(true)
    expect(w.findAll('.ptd-status-select option')).toHaveLength(4)
  })
})
