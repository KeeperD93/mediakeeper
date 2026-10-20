import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'

const tickets = ref([])
const total = ref(0)
const loading = ref(false)
const fetchTickets = vi.fn(() => Promise.resolve())
const createTicket = vi.fn(() => Promise.resolve({ success: true }))

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
}))

vi.mock('vue-i18n', () => ({
  useI18n: () => ({ t: key => key }),
}))

vi.mock('@/composables/portal/usePortalTickets', () => ({
  usePortalTickets: () => ({
    tickets,
    total,
    loading,
    fetchTickets,
    createTicket,
  }),
}))

const showToast = vi.fn()
vi.mock('@/composables/useToast', () => ({
  useToast: () => ({ showToast }),
}))
vi.mock('@/composables/useApi', () => ({
  resolveApiError: (code, fallbackKey) => fallbackKey,
}))

vi.mock('@/components/portal/tickets/TicketCard.vue', () => ({
  default: { name: 'TicketCard', props: ['ticket'], template: '<div class="tc-stub" />' },
}))
vi.mock('@/components/portal/tickets/EmbyMediaPicker.vue', () => ({
  default: { name: 'EmbyMediaPicker', template: '<div />' },
}))
vi.mock('@/components/portal/tickets/TicketSeasonPicker.vue', () => ({
  default: { name: 'TicketSeasonPicker', template: '<div />' },
}))

import PortalTickets from '@/views/portal/PortalTickets.vue'

describe('PortalTickets — toolbar', () => {
  beforeEach(() => {
    tickets.value = []
    fetchTickets.mockClear()
    createTicket.mockClear()
  })

  // Regression guard — the "Source" (media_type) filter was retired with
  // this refonte. It must never resurface accidentally.
  it('does not render the legacy Source/media-type filter', async () => {
    const w = mount(PortalTickets)
    await flushPromises()
    const html = w.html()
    expect(html).not.toContain('portal.tickets.list.filterScope')
    expect(html).not.toContain('portal.tickets.list.scopeLibrary')
    expect(html).not.toContain('portal.tickets.list.scopeMovies')
    expect(html).not.toContain('portal.tickets.list.scopeSeries')
    expect(html).not.toContain('portal.tickets.list.scopeOther')
  })

  it('renders the sort select with newest + oldest only', async () => {
    const w = mount(PortalTickets)
    await flushPromises()
    const selects = w.findAll('.ptl-toolbar-select')
    // Two toolbar selects: type then sort.
    expect(selects).toHaveLength(2)
    const sortOptions = selects[1].findAll('option')
    expect(sortOptions).toHaveLength(2)
    expect(sortOptions.map(o => o.attributes('value'))).toEqual(['newest', 'oldest'])
  })

  it('gives both toolbar menus the shared chevron, clear of the right edge', async () => {
    const w = mount(PortalTickets)
    await flushPromises()
    const chevrons = w.findAll('.ptl-toolbar-select').map(s => s.classes('mk-select-chevron'))
    expect(chevrons).toEqual([true, true])
  })

  it('renders the issue-type select with the "all" entry + 7 concrete types', async () => {
    const w = mount(PortalTickets)
    await flushPromises()
    const typeSelect = w.findAll('.ptl-toolbar-select')[0]
    const options = typeSelect.findAll('option')
    expect(options).toHaveLength(8)
    expect(options[0].attributes('value')).toBe('')
    expect(options.slice(1).map(o => o.attributes('value'))).toEqual([
      'audio',
      'subtitles',
      'video',
      'metadata',
      'playback',
      'file',
      'other',
    ])
  })

  it('passes the selected sort order to fetchTickets', async () => {
    const w = mount(PortalTickets)
    await flushPromises()
    fetchTickets.mockClear()
    const sortSelect = w.findAll('.ptl-toolbar-select')[1]
    await sortSelect.setValue('oldest')
    expect(fetchTickets).toHaveBeenCalledWith(expect.objectContaining({ sort: 'oldest' }))
  })
})

describe('PortalTickets — status pills and reporting', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.spyOn(console, 'error').mockImplementation(() => {})
  })

  it('marks the active status pill as pressed', async () => {
    const w = mount(PortalTickets)
    await flushPromises()
    const pills = w.findAll('.ptl-toolbar-pills .arr-pill')

    await pills[1].trigger('click')

    expect(pills.map(p => p.attributes('aria-pressed'))).toEqual([
      'false',
      'true',
      'false',
      'false',
      'false',
    ])
  })

  it('keeps the form open and says the report could not be sent', async () => {
    createTicket.mockRejectedValueOnce(new Error('http_500'))
    const w = mount(PortalTickets, { global: { stubs: { TicketCreateModal: true } } })
    await flushPromises()

    await w.find('.ptl-create').trigger('click')
    w.findComponent({ name: 'TicketCreateModal' }).vm.$emit('submit', { description: 'x' })
    await flushPromises()

    expect(showToast).toHaveBeenCalledWith('portal.tickets.createFailed', 'err')
    expect(w.findComponent({ name: 'TicketCreateModal' }).exists()).toBe(true)
  })
})
