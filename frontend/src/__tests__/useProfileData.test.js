import { describe, it, expect, vi, beforeEach } from 'vitest'

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
vi.mock('@/composables/portal/useAvailability', () => ({
  useAvailability: () => ({ checkAvailability: vi.fn() }),
}))
vi.mock('@/composables/portal/useRequestStatus', () => ({
  useRequestStatus: () => ({ checkStatus: vi.fn() }),
}))

import { useProfileData, markTrophyShown } from '@/composables/portal/useProfileData'

const TROPHY_KEY = 'portal_shown_trophy_unlocks_v1'

function makeTrophy(id, secondsAgo, status = 'unlocked') {
  return {
    id,
    status,
    unlocked_at: new Date(Date.now() - secondsAgo * 1000).toISOString(),
  }
}

describe('useProfileData — trophy unlock deduplication', () => {
  beforeEach(() => {
    localStorage.clear()
    apiGet.mockReset()
  })

  it('surfaces a freshly-unlocked trophy that has not been celebrated yet', async () => {
    apiGet.mockImplementation(url => {
      if (url.includes('achievements/me')) {
        return Promise.resolve({ items: [makeTrophy(101, 30)] })
      }
      return Promise.resolve(null)
    })
    const profile = useProfileData()
    await profile.load()
    expect(profile.recentUnlock.value?.id).toBe(101)
  })

  it('skips trophies whose IDs are already cached in localStorage', async () => {
    localStorage.setItem(TROPHY_KEY, JSON.stringify([42]))
    apiGet.mockImplementation(url => {
      if (url.includes('achievements/me')) {
        return Promise.resolve({ items: [makeTrophy(42, 30)] })
      }
      return Promise.resolve(null)
    })
    const profile = useProfileData()
    await profile.load()
    expect(profile.recentUnlock.value).toBeNull()
  })

  it('markTrophyShown appends to localStorage and caps at 50 entries', () => {
    for (let i = 0; i < 60; i++) markTrophyShown(i)
    const stored = JSON.parse(localStorage.getItem(TROPHY_KEY))
    expect(stored.length).toBe(50)
    // The cap keeps the most recent 50 — entries 10..59.
    expect(stored[0]).toBe(10)
    expect(stored[stored.length - 1]).toBe(59)
  })
})
