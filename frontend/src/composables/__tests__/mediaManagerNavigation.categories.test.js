import { describe, it, expect, vi, beforeEach } from 'vitest'

// vi.mock is hoisted, so the refs it returns are created via vi.hoisted.
// loadCategories only touches apiGet, CATS, catsLoaded and activeCat; the
// other state exports are stubbed so the module's top-level destructuring
// import does not blow up.
const h = vi.hoisted(() => ({
  apiGet: vi.fn(),
  CATS: { value: [] },
  catsLoaded: { value: false },
  activeCat: { value: 'telechargement' },
}))

vi.mock('@/composables/mediaManagerState', () => ({
  apiGet: h.apiGet,
  apiFetch: vi.fn(),
  showToast: vi.fn(),
  _t: k => k,
  CATS: h.CATS,
  catsLoaded: h.catsLoaded,
  activeCat: h.activeCat,
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

import { loadCategories } from '@/composables/mediaManagerNavigation'

const CATS_FIXTURE = [
  { key: 'films', label: 'Films' },
  { key: 'series', label: 'Series' },
  { key: 'telechargement', label: 'Téléchargement' },
]

describe('loadCategories — default tab', () => {
  beforeEach(() => {
    h.apiGet.mockReset()
    h.CATS.value = []
    h.catsLoaded.value = false
    h.activeCat.value = 'telechargement'
  })

  it('selects the leftmost category on load, even when the current tab is still valid', async () => {
    h.apiGet.mockResolvedValue(CATS_FIXTURE)
    await loadCategories()
    expect(h.activeCat.value).toBe('films')
    expect(h.CATS.value).toEqual(CATS_FIXTURE)
    expect(h.catsLoaded.value).toBe(true)
  })

  it('leaves state untouched when the API returns no categories', async () => {
    h.apiGet.mockResolvedValue([])
    await loadCategories()
    expect(h.activeCat.value).toBe('telechargement')
    expect(h.catsLoaded.value).toBe(false)
  })
})
