/**
 * Miss-payload contract on ``useAvailability``.
 *
 * The backend returns ``null`` for tmdb_ids that aren't in
 * ``EmbyTmdbIndex`` yet (freshly added Emby items lag the indexer).
 * The cache must flag that as ``_empty`` so ``getAvailability``
 * returns null and ``MediaCard``'s inline fallback can stamp the
 * "Dispo" badge from the ``/library/recent`` payload.
 *
 * We also pin the forward-compat shim: an older API revision used
 * to return ``{availability:null, emby_item_id:null, emby_url:null}``
 * instead of bare ``null``. That object must be treated the same as
 * a real null — otherwise the cache stores a "phantom hit" that
 * erases the inline badge ~0.5 s after page load.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'

const apiPost = vi.fn()
vi.mock('@/composables/useApi', () => ({
  useApi: () => ({ apiPost }),
}))

import { useAvailability } from '@/composables/portal/useAvailability'

async function flushMicrotasks() {
  await Promise.resolve()
  await Promise.resolve()
}

describe('useAvailability — miss payload handling', () => {
  beforeEach(() => {
    apiPost.mockReset()
    const { clearCache } = useAvailability()
    clearCache()
  })

  it('flags a bare null payload as empty so getAvailability returns null', async () => {
    apiPost.mockResolvedValueOnce({ results: { 999: null } })
    const { checkAvailability, getAvailability } = useAvailability()

    await Promise.all([
      checkAvailability([{ tmdb_id: 999, media_type: 'movie' }]),
      flushMicrotasks(),
    ])

    expect(getAvailability(999)).toBeNull()
  })

  it('flags an all-null object payload as empty (legacy backend shape)', async () => {
    apiPost.mockResolvedValueOnce({
      results: {
        1376415: { availability: null, emby_item_id: null, emby_url: null },
      },
    })
    const { checkAvailability, getAvailability } = useAvailability()

    await Promise.all([
      checkAvailability([{ tmdb_id: 1376415, media_type: 'movie' }]),
      flushMicrotasks(),
    ])

    expect(getAvailability(1376415)).toBeNull()
  })

  it('still stores a real hit verbatim (regression guard)', async () => {
    apiPost.mockResolvedValueOnce({
      results: {
        42: { availability: 'full', emby_item_id: 'abc', emby_url: '/e/42' },
      },
    })
    const { checkAvailability, getAvailability } = useAvailability()

    await Promise.all([
      checkAvailability([{ tmdb_id: 42, media_type: 'movie' }]),
      flushMicrotasks(),
    ])

    const entry = getAvailability(42)
    expect(entry).not.toBeNull()
    expect(entry.availability).toBe('full')
    expect(entry.emby_item_id).toBe('abc')
    expect(entry.emby_url).toBe('/e/42')
  })
})
