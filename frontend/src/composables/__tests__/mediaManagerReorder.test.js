import { describe, it, expect, vi, beforeEach } from 'vitest'

// vi.mock is hoisted; the spies/refs it references come from vi.hoisted.
const h = vi.hoisted(() => ({
  apiFetch: vi.fn(),
  CATS: { value: [] },
}))

vi.mock('@/composables/mediaManagerState', () => ({
  apiGet: vi.fn(),
  apiFetch: h.apiFetch,
  showToast: vi.fn(),
  _t: k => k,
  CATS: h.CATS,
  catsLoaded: { value: false },
  activeCat: { value: '' },
  // Remaining named exports destructured at import (unused by reorderCategories).
  subPath: { value: '' },
  files: { value: [] },
  filtered: { value: [] },
  checked: { value: new Set() },
  loading: { value: false },
  filterQuery: { value: '' },
  sortMode: { value: 'name-asc' },
  expandedMode: { value: false },
  tags: { value: {} },
  selectedTmdb: { value: null },
  tmdbResults: { value: [] },
  showSeasonPanel: { value: false },
  newNames: { value: [] },
  multiCatMode: { value: false },
  namingIssues: { value: {} },
  analysisActive: { value: false },
  newFileThresholdMs: 0,
  _autoSearchState: {},
}))
vi.mock('@/composables/useConfirm', () => ({ useConfirm: () => vi.fn() }))

import { reorderCategories } from '@/composables/mediaManagerNavigation'

const CATS_FIXTURE = [
  { key: 'films', label: 'Films' },
  { key: 'series', label: 'Series' },
  { key: 'dl', label: 'DL' },
]
const fakeRes = body => ({ json: async () => body })

describe('reorderCategories', () => {
  beforeEach(() => {
    h.apiFetch.mockReset()
    h.CATS.value = [...CATS_FIXTURE]
  })

  it('reorders optimistically, PUTs the keys, and keeps the server order', async () => {
    h.apiFetch.mockResolvedValue(
      fakeRes({
        ok: true,
        categories: [
          { key: 'dl', label: 'DL' },
          { key: 'films', label: 'Films' },
          { key: 'series', label: 'Series' },
        ],
      }),
    )
    const ok = await reorderCategories(['dl', 'films', 'series'])
    expect(ok).toBe(true)
    const [url, opts] = h.apiFetch.mock.calls[0]
    expect(url).toBe('/api/media/categories/order')
    expect(opts.method).toBe('PUT')
    expect(JSON.parse(opts.body)).toEqual({ keys: ['dl', 'films', 'series'] })
    expect(h.CATS.value.map(c => c.key)).toEqual(['dl', 'films', 'series'])
  })

  it('reverts to the original order when the backend rejects', async () => {
    h.apiFetch.mockResolvedValue(fakeRes({ error: 'category_set_mismatch' }))
    const ok = await reorderCategories(['dl', 'films', 'series'])
    expect(ok).toBe(false)
    expect(h.CATS.value.map(c => c.key)).toEqual(['films', 'series', 'dl'])
  })
})
