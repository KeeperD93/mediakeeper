import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { ref } from 'vue'

const profileRef = ref({ user_id: 17, role: 'viewer' })

vi.mock('vue-i18n', () => ({
  useI18n: () => ({
    t: (key, params) => (params ? `${key}:${JSON.stringify(params)}` : key),
  }),
}))

vi.mock('@/composables/portal/usePortalAuth', () => ({
  usePortalAuth: () => ({ profile: profileRef }),
}))

import TicketThread from '@/components/portal/tickets/TicketThread.vue'

const BASE_TICKET = {
  id: 42,
  description: 'Audio désynchronisé',
  status: 'open',
  created_at: new Date(Date.now() - 30 * 60 * 1000).toISOString(),
  requester: {
    user_id: 17,
    display_name: 'Xyrel',
    avatar_url: 'https://x.test/a.jpg',
    role: 'viewer',
  },
  replies: [],
}

describe('TicketThread', () => {
  beforeEach(() => {
    profileRef.value = { user_id: 17, role: 'viewer' }
  })

  it('renders the description as the first bubble', () => {
    const w = mount(TicketThread, { props: { ticket: BASE_TICKET } })
    const rows = w.findAll('.tth-row')
    expect(rows).toHaveLength(1)
    expect(rows[0].text()).toContain('Audio désynchronisé')
    expect(rows[0].text()).toContain('Xyrel')
  })

  it('marks the requester bubble as "mine" when their user_id matches the viewer', () => {
    const w = mount(TicketThread, { props: { ticket: BASE_TICKET } })
    expect(w.find('.tth-row--mine').exists()).toBe(true)
  })

  it('renders an admin role badge for admin authors', () => {
    const ticket = {
      ...BASE_TICKET,
      replies: [{
        id: 1,
        content: 'Pris en charge.',
        created_at: new Date().toISOString(),
        author: { user_id: 1, display_name: 'Admin', role: 'admin', avatar_url: null },
      }],
    }
    const w = mount(TicketThread, { props: { ticket } })
    expect(w.find('.tth-role-pill').exists()).toBe(true)
    expect(w.find('.tth-row--admin').exists()).toBe(true)
  })

  it('shows the resolved footer when the ticket is resolved', () => {
    const w = mount(TicketThread, {
      props: { ticket: { ...BASE_TICKET, status: 'resolved' } },
    })
    expect(w.find('.tth-status-footer--resolved').exists()).toBe(true)
  })

  it('hides the reply form when the ticket is closed', () => {
    const w = mount(TicketThread, {
      props: { ticket: { ...BASE_TICKET, status: 'closed' } },
    })
    expect(w.find('.tth-form').exists()).toBe(false)
    expect(w.find('.tth-status-footer--closed').exists()).toBe(true)
  })

  it('emits the typed reply on submit and clears the textarea', async () => {
    const w = mount(TicketThread, { props: { ticket: BASE_TICKET } })
    const ta = w.find('.tth-input')
    await ta.setValue('Bonjour, je confirme le bug.')
    await w.find('.tth-form').trigger('submit')

    const emitted = w.emitted('reply')
    expect(emitted).toBeTruthy()
    expect(emitted[0][0]).toBe('Bonjour, je confirme le bug.')
    expect(ta.element.value).toBe('')
  })

  it('falls back to the first letter when no avatar_url is provided', () => {
    const ticket = {
      ...BASE_TICKET,
      requester: { ...BASE_TICKET.requester, avatar_url: null },
    }
    const w = mount(TicketThread, { props: { ticket } })
    expect(w.find('.tth-avatar--fallback').exists()).toBe(true)
    expect(w.find('.tth-avatar--fallback').text()).toBe('X')
  })
})
