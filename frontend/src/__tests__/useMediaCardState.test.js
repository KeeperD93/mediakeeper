import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useMediaCardState } from '@/composables/portal/useMediaCardState'

// Mock i18n + collaborators
vi.mock('vue-i18n', () => ({
  useI18n: () => ({ t: (key) => key }),
}))

const mockAvailability = { value: null }
vi.mock('@/composables/portal/useAvailability', () => ({
  useAvailability: () => ({
    getAvailability: vi.fn(() => mockAvailability.value),
  }),
}))

vi.mock('@/composables/portal/useRequestStatus', () => ({
  useRequestStatus: () => ({
    getStatus: vi.fn(() => null),
  }),
}))

describe('useMediaCardState — availData fallback chain', () => {
  beforeEach(() => {
    mockAvailability.value = null
  })

  it('uses canonical cache when getAvailability returns a populated entry', () => {
    mockAvailability.value = { availability: 'partial', emby_url: '/emby/123', _ts: Date.now() }
    const item = { tmdb_id: 42, emby_url: '/inline-stale', availability: 'full' }
    const { availData } = useMediaCardState({ item })
    expect(availData.value.availability).toBe('partial')
    expect(availData.value.emby_url).toBe('/emby/123')
  })

  it('falls back to inline emby_url/availability when cache miss returns null', () => {
    mockAvailability.value = null
    const item = { tmdb_id: 42, emby_url: '/inline', availability: 'full' }
    const { availData } = useMediaCardState({ item })
    expect(availData.value.availability).toBe('full')
    expect(availData.value.emby_url).toBe('/inline')
  })

  it('returns null when neither cache nor inline data is present', () => {
    mockAvailability.value = null
    const item = { tmdb_id: 42 }
    const { availData } = useMediaCardState({ item })
    expect(availData.value).toBeNull()
  })

  it('still uses inline fallback when item has no tmdb_id (cache lookup is skipped)', () => {
    mockAvailability.value = { availability: 'full', _ts: Date.now() } // would match if id existed
    const item = { availability: 'full', emby_url: '/inline' }
    const { availData } = useMediaCardState({ item })
    expect(availData.value.availability).toBe('full')
    expect(availData.value.emby_url).toBe('/inline')
  })
})
