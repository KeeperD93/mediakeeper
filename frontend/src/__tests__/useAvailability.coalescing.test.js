/**
 * Coalescing contract on ``useAvailability``.
 *
 * The Portal home fires ~13 carousels in parallel, and each one used
 * to POST /availability the moment its data resolved — swamping the
 * endpoint and stacking rate-limit toasts. The composable now batches
 * every call landing inside the same microtask tick into a single
 * POST with the deduped union of items.
 *
 * We pin two invariants here:
 *
 *   1. Three sync calls in a row produce exactly one POST whose body
 *      is the union of their items (with duplicate tmdb_ids removed).
 *   2. After the flush, a new caller starts a fresh batch — the queue
 *      is not "consumed once and dead" because the home reloads
 *      periodically.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'

const apiPost = vi.fn()
vi.mock('@/composables/useApi', () => ({
  useApi: () => ({ apiPost }),
}))

import { useAvailability } from '@/composables/portal/useAvailability'

async function flushMicrotasks() {
  // Two awaits: queueMicrotask schedules _flushQueue, which then
  // awaits the apiPost promise — both have to resolve before the
  // post-flush state is observable.
  await Promise.resolve()
  await Promise.resolve()
}

describe('useAvailability — microtask coalescing', () => {
  beforeEach(() => {
    apiPost.mockReset()
    apiPost.mockResolvedValue({ results: {} })
    // Drop the module-shared cache so a previous test's stamps don't
    // make this run skip the dedupe path entirely.
    const { clearCache } = useAvailability()
    clearCache()
  })

  it('collapses three sync calls into a single POST with deduped items', async () => {
    const { checkAvailability } = useAvailability()

    const p1 = checkAvailability([{ tmdb_id: 1, media_type: 'movie' }])
    const p2 = checkAvailability([{ tmdb_id: 2, media_type: 'movie' }])
    // Repeat id 1 — must be deduped against the queued payload.
    const p3 = checkAvailability([
      { tmdb_id: 3, media_type: 'tv' },
      { tmdb_id: 1, media_type: 'movie' },
    ])

    await Promise.all([p1, p2, p3, flushMicrotasks()])

    expect(apiPost).toHaveBeenCalledTimes(1)
    const [url, body] = apiPost.mock.calls[0]
    expect(url).toBe('/api/portal/availability')
    const ids = body.items.map(i => i.tmdb_id).sort()
    expect(ids).toEqual([1, 2, 3])
  })

  it('starts a fresh batch after the previous flush', async () => {
    const { checkAvailability } = useAvailability()

    await Promise.all([
      checkAvailability([{ tmdb_id: 10, media_type: 'movie' }]),
      flushMicrotasks(),
    ])
    expect(apiPost).toHaveBeenCalledTimes(1)

    await Promise.all([
      checkAvailability([{ tmdb_id: 20, media_type: 'movie' }]),
      flushMicrotasks(),
    ])
    expect(apiPost).toHaveBeenCalledTimes(2)
    expect(apiPost.mock.calls[1][1].items[0].tmdb_id).toBe(20)
  })

  it('skips the POST entirely when every item is fresh in the cache', async () => {
    const { checkAvailability } = useAvailability()

    apiPost.mockResolvedValueOnce({
      results: {
        42: { availability: 'full', emby_item_id: 'x', emby_url: 'u' },
      },
    })
    await Promise.all([
      checkAvailability([{ tmdb_id: 42, media_type: 'movie' }]),
      flushMicrotasks(),
    ])
    expect(apiPost).toHaveBeenCalledTimes(1)

    // Second call within the TTL window should not trigger another POST.
    await Promise.all([
      checkAvailability([{ tmdb_id: 42, media_type: 'movie' }]),
      flushMicrotasks(),
    ])
    expect(apiPost).toHaveBeenCalledTimes(1)
  })
})
