import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import TicketSeasonPicker from '@/components/portal/tickets/TicketSeasonPicker.vue'

const fetchSeriesSeasons = vi.fn()

vi.mock('vue-i18n', () => ({
  useI18n: () => ({
    t: (key, params) => (params ? `${key}:${JSON.stringify(params)}` : key),
  }),
}))

vi.mock('@/composables/portal/usePortalTicketEmby', () => ({
  usePortalTicketEmby: () => ({
    results: { value: [] },
    searching: { value: false },
    lastQuery: { value: '' },
    searchDebounced: vi.fn(),
    clearResults: vi.fn(),
    fetchSeriesSeasons,
    MIN_QUERY_LENGTH: 2,
  }),
}))

const SAMPLE_SEASONS = [
  {
    season_number: 1,
    name: 'Saison 1',
    episodes: [
      { id: 'e1', episode_number: 1, name: 'Pilot' },
      { id: 'e2', episode_number: 2, name: 'Half Loop' },
      { id: 'e3', episode_number: 3, name: 'In Perpetuity' },
    ],
  },
  {
    season_number: 2,
    name: 'Saison 2',
    episodes: [
      { id: 'e4', episode_number: 1, name: 'Hello, Ms. Cobel' },
      { id: 'e5', episode_number: 2, name: 'Goodbye, Mrs. Selvig' },
    ],
  },
]

async function mountPicker() {
  fetchSeriesSeasons.mockResolvedValue(SAMPLE_SEASONS)
  const w = mount(TicketSeasonPicker, { props: { seriesId: 'emby-ser-42' } })
  await flushPromises()
  return w
}

describe('TicketSeasonPicker', () => {
  beforeEach(() => {
    fetchSeriesSeasons.mockReset()
  })

  it('emits "series" + null payload by default (whole series)', async () => {
    const w = await mountPicker()
    // Two emits total: the empty initial, then the post-load empty.
    const emits = w.emitted('update:selection')
    expect(emits).toBeTruthy()
    const last = emits[emits.length - 1][0]
    expect(last.media_type).toBe('series')
    expect(last.selected_seasons).toBeNull()
  })

  it('emits "season" media_type when a whole season is checked', async () => {
    const w = await mountPicker()
    await w.find('.tsp-season-header .tsp-chk').setValue(true)
    const last = w.emitted('update:selection').at(-1)[0]
    expect(last.media_type).toBe('season')
    expect(last.selected_seasons).toEqual([{ season_number: 1 }])
  })

  it('emits "episode" media_type when individual episodes are checked', async () => {
    const w = await mountPicker()
    // Expand season 1.
    await w.find('.tsp-season-header').trigger('click')
    const epBoxes = w.findAll('.tsp-episode .tsp-chk')
    await epBoxes[0].setValue(true)
    await epBoxes[2].setValue(true)

    const last = w.emitted('update:selection').at(-1)[0]
    expect(last.media_type).toBe('episode')
    expect(last.selected_seasons).toEqual([
      { season_number: 1, episodes: [1, 3] },
    ])
  })

  it('reset button clears the selection back to the whole series', async () => {
    const w = await mountPicker()
    await w.find('.tsp-season-header .tsp-chk').setValue(true)
    expect(w.emitted('update:selection').at(-1)[0].media_type).toBe('season')

    await w.find('.tsp-clear').trigger('click')
    const last = w.emitted('update:selection').at(-1)[0]
    expect(last.media_type).toBe('series')
    expect(last.selected_seasons).toBeNull()
  })

  it('shows the empty state when the series has no seasons', async () => {
    fetchSeriesSeasons.mockResolvedValue([])
    const w = mount(TicketSeasonPicker, { props: { seriesId: 'no-such-series' } })
    await flushPromises()
    expect(w.text()).toContain('portal.tickets.seasonPicker.empty')
  })
})
