/**
 * Admin history tabs (Notifications + Duplicates) — cursor "Load more"
 * pagination wired into useNotifs / useDuplicates.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'

const apiGet = vi.fn()

vi.mock('@/composables/useApi', () => ({
  useApi: () => ({ apiGet, apiFetch: vi.fn(), apiPost: vi.fn(), apiDelete: vi.fn() }),
}))
vi.mock('@/composables/useToast', () => ({ useToast: () => ({ showToast: vi.fn() }) }))
vi.mock('@/composables/useConfirm', () => ({
  useConfirm: () => vi.fn(() => Promise.resolve(true)),
}))
vi.mock('vue-i18n', () => ({ useI18n: () => ({ t: k => k }) }))
// Avoid pulling the real i18n singleton (via datetime) into this unit test.
vi.mock('@/utils/datetime', () => ({ localizedDate: () => '' }))

import { useDuplicates } from '@/composables/useDuplicates'
import { useNotifs } from '@/composables/useNotifs'

beforeEach(() => apiGet.mockReset())

describe('useDuplicates — history pagination', () => {
  it('loads the first page then appends the next via the cursor', async () => {
    const d = useDuplicates()

    apiGet.mockResolvedValueOnce({
      items: [{ id: 3 }, { id: 2 }],
      next_cursor: 'c1',
      has_more: true,
    })
    await d.loadHistory()
    expect(d.history.value.map(h => h.id)).toEqual([3, 2])
    expect(d.historyHasMore.value).toBe(true)

    apiGet.mockResolvedValueOnce({ items: [{ id: 1 }], next_cursor: null, has_more: false })
    await d.loadHistory(true)
    expect(d.history.value.map(h => h.id)).toEqual([3, 2, 1])
    expect(d.historyHasMore.value).toBe(false)
    expect(apiGet).toHaveBeenLastCalledWith(expect.stringContaining('cursor=c1'))
  })

  it('does not fetch more once the last page is reached', async () => {
    const d = useDuplicates()
    apiGet.mockResolvedValueOnce({ items: [{ id: 1 }], next_cursor: null, has_more: false })
    await d.loadHistory()
    apiGet.mockClear()
    await d.loadHistory(true)
    expect(apiGet).not.toHaveBeenCalled()
  })
})

describe('useNotifs — history pagination', () => {
  it('loads the first page then appends the next', async () => {
    const n = useNotifs()

    apiGet.mockResolvedValueOnce({ items: [{ id: 5 }], next_cursor: 'cX', has_more: true })
    await n.loadHistory()
    expect(n.history.value.map(h => h.id)).toEqual([5])
    expect(n.historyHasMore.value).toBe(true)

    apiGet.mockResolvedValueOnce({ items: [{ id: 4 }], next_cursor: null, has_more: false })
    await n.loadHistory(true)
    expect(n.history.value.map(h => h.id)).toEqual([5, 4])
    expect(n.historyHasMore.value).toBe(false)
  })
})
