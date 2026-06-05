/**
 * Chunking contract on ``useRequestStatus``.
 *
 * The backend caps batch-status at BATCH_STATUS_MAX_IDS (100) unique ids
 * and 422s past it. A large view (multi-carousel home, infinite scroll,
 * cold cache) used to POST every id at once and silently lose all
 * "already requested" badges for the batch. ``checkStatus`` now splits
 * into capped chunks run in parallel, and a single chunk failure no
 * longer wipes the badges the other chunks resolved.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'

const apiPost = vi.fn()
vi.mock('@/composables/useApi', () => ({
  useApi: () => ({ apiPost }),
}))

import { useRequestStatus } from '@/composables/portal/useRequestStatus'

const items = n => Array.from({ length: n }, (_, i) => ({ tmdb_id: i + 1 }))

describe('useRequestStatus — chunking', () => {
  beforeEach(() => {
    apiPost.mockReset()
    apiPost.mockResolvedValue({ results: {} })
    useRequestStatus().clearCache()
  })

  it('splits more than 100 ids into capped parallel chunks', async () => {
    await useRequestStatus().checkStatus(items(150))

    expect(apiPost).toHaveBeenCalledTimes(2)
    const sizes = apiPost.mock.calls.map(c => c[1].tmdb_ids.length)
    expect(Math.max(...sizes)).toBeLessThanOrEqual(100)
    expect(sizes.reduce((a, b) => a + b, 0)).toBe(150)
  })

  it('sends a single chunk for 100 or fewer ids', async () => {
    await useRequestStatus().checkStatus(items(100))
    expect(apiPost).toHaveBeenCalledTimes(1)
    expect(apiPost.mock.calls[0][1].tmdb_ids).toHaveLength(100)
  })

  it('merges results from every chunk into the cache', async () => {
    apiPost.mockImplementation((_url, body) =>
      Promise.resolve({
        results: { [body.tmdb_ids[0]]: { status: 'pending', requested_at: 'x' } },
      }),
    )
    const { checkStatus, getStatus } = useRequestStatus()
    await checkStatus(items(150))

    expect(getStatus(1)?.status).toBe('pending') // first id of chunk 1
    expect(getStatus(101)?.status).toBe('pending') // first id of chunk 2
  })

  it('keeps badges from successful chunks when one chunk fails', async () => {
    apiPost.mockImplementation((_url, body) =>
      body.tmdb_ids.includes(101)
        ? Promise.reject(new Error('boom'))
        : Promise.resolve({ results: { 1: { status: 'approved', requested_at: 'x' } } }),
    )
    const { checkStatus, getStatus } = useRequestStatus()
    await checkStatus(items(150))

    expect(getStatus(1)?.status).toBe('approved') // successful chunk survived the failure
    expect(getStatus(101)).toBeNull() // failed chunk's ids left unstamped to retry
  })
})
