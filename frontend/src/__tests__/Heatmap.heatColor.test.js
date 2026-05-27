/**
 * Covers the `heatColor` bucket logic in Heatmap.vue — verifies that
 * each play-count threshold (0 / 1-4 / 5-12 / 13-25 / 26+) returns
 * the correct `--heat-N` CSS variable. The function is private to the
 * SFC, so the test mounts the component with a mocked apiGet that
 * forces specific counts on the heatmap days and then inspects each
 * cell's inline background style.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

const apiGet = vi.fn()

vi.mock('@/composables/useApi', () => ({
  useApi: () => ({
    apiGet,
    apiPost: vi.fn(),
    apiPut: vi.fn(),
    apiDelete: vi.fn(),
    apiPatch: vi.fn(),
    apiFetch: vi.fn(),
    loading: { value: false },
    error: { value: null },
  }),
}))

vi.mock('vue-i18n', () => ({
  useI18n: () => ({ t: key => key }),
}))

import Heatmap from '@/components/dashboard/widgets/Heatmap.vue'

const FIXED_NOW = new Date('2026-06-15T12:00:00Z').getTime()

function isoOffset(days) {
  const d = new Date(FIXED_NOW)
  d.setUTCDate(d.getUTCDate() - days)
  return d.toISOString().slice(0, 10)
}

/**
 * Build an apiGet response payload that assigns one explicit play
 * count to each of the first 5 days (oldest in the 84-day window).
 * The remaining days stay at 0 (default) so we know the matching
 * cell indexes by ordering.
 */
function buildResponse(counts) {
  const data = {}
  counts.forEach((count, i) => {
    // Offset 83 - i so the first count ends up on the oldest cell
    // and the order in the rendered grid matches the input array.
    data[isoOffset(83 - i)] = { films: { plays: count } }
  })
  return { data }
}

describe('Heatmap — heatColor buckets', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(FIXED_NOW)
    apiGet.mockReset()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('maps play counts to the correct --heat-N CSS variable', async () => {
    // One count per bucket boundary, plus a high outlier.
    const counts = [0, 4, 12, 25, 26]
    apiGet.mockResolvedValueOnce(buildResponse(counts))

    const w = mount(Heatmap)
    await flushPromises()

    const cells = w.findAll('.hm-cell:not(.hm-legend-cell)')
    expect(cells.length).toBe(84)

    const expected = [
      'var(--heat-0)',
      'var(--heat-1)',
      'var(--heat-2)',
      'var(--heat-3)',
      'var(--heat-4)',
    ]
    for (let i = 0; i < expected.length; i++) {
      expect(cells[i].attributes('style')).toContain(expected[i])
    }

    w.unmount()
  })

  it('groups counts within the same bucket onto the same heat level', async () => {
    // Inside bucket #1 (1..4) and bucket #2 (5..12).
    const counts = [1, 3, 4, 5, 7, 12]
    apiGet.mockResolvedValueOnce(buildResponse(counts))

    const w = mount(Heatmap)
    await flushPromises()

    const cells = w.findAll('.hm-cell:not(.hm-legend-cell)')
    // 1, 3, 4 → heat-1
    for (let i = 0; i < 3; i++) {
      expect(cells[i].attributes('style')).toContain('var(--heat-1)')
    }
    // 5, 7, 12 → heat-2
    for (let i = 3; i < 6; i++) {
      expect(cells[i].attributes('style')).toContain('var(--heat-2)')
    }

    w.unmount()
  })

  it('renders the full 5-step legend regardless of data', async () => {
    apiGet.mockResolvedValueOnce({ data: {} })

    const w = mount(Heatmap)
    await flushPromises()

    const legendCells = w.findAll('.hm-legend-cell')
    expect(legendCells.length).toBe(5)
    expect(legendCells[0].attributes('style')).toContain('var(--heat-0)')
    expect(legendCells[4].attributes('style')).toContain('var(--heat-4)')

    w.unmount()
  })
})
