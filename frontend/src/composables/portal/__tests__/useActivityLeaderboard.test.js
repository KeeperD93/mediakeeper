/**
 * Ranking of a period: one memo per period and size, one request at a time for each,
 * and the last tab clicked decides what the page shows.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const apiGet = vi.fn()

vi.mock('@/composables/useApi', () => ({
  useApi: () => ({ apiGet }),
}))

const payload = name => ({
  items: [{ rank: 1, display_name: name }],
  viewer_rank: 4,
  viewer_entry: { rank: 4, display_name: 'Alice' },
  stats: { period_label: name },
})

function deferred() {
  let resolve, reject
  const promise = new Promise((res, rej) => {
    resolve = res
    reject = rej
  })
  return { promise, resolve, reject }
}

// The memo lives in the module: a fresh import starts each test without it.
async function freshComposable() {
  vi.resetModules()
  const { useActivityLeaderboard } = await import('@/composables/portal/useActivityLeaderboard')
  return useActivityLeaderboard()
}

describe('useActivityLeaderboard', () => {
  beforeEach(() => {
    apiGet.mockReset()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('asks the server for the month unless told otherwise', async () => {
    apiGet.mockResolvedValue(payload('Month'))
    const { fetchTop, entries, viewerRank, viewerEntry, stats } = await freshComposable()

    await fetchTop()

    expect(apiGet).toHaveBeenCalledWith(
      '/api/portal/achievements/leaderboard/activity?period=month&limit=100',
    )
    expect(entries.value[0].display_name).toBe('Month')
    expect(viewerRank.value).toBe(4)
    expect(viewerEntry.value.display_name).toBe('Alice')
    expect(stats.value.period_label).toBe('Month')
  })

  it('asks for the period and the size it is given', async () => {
    apiGet.mockResolvedValue(payload('Week'))
    const { fetchTop } = await freshComposable()

    await fetchTop(15, { period: 'week' })

    expect(apiGet).toHaveBeenCalledWith(
      '/api/portal/achievements/leaderboard/activity?period=week&limit=15',
    )
  })

  it('serves a period already seen from its memo, without a request or a wait', async () => {
    apiGet.mockImplementation(url => Promise.resolve(payload(url.match(/period=(\w+)/)[1])))
    const { fetchTop, entries, loading } = await freshComposable()
    await fetchTop(100, { period: 'week' })
    await fetchTop(100, { period: 'all' })
    apiGet.mockClear()

    const back = fetchTop(100, { period: 'week' })

    expect(entries.value[0].display_name).toBe('week')
    expect(loading.value).toBe(false)
    await back
    expect(apiGet).not.toHaveBeenCalled()
  })

  it('keeps apart two sizes of the same period', async () => {
    apiGet.mockResolvedValue(payload('Week'))
    const { fetchTop } = await freshComposable()

    await fetchTop(100, { period: 'week' })
    await fetchTop(15, { period: 'week' })

    expect(apiGet).toHaveBeenCalledTimes(2)
  })

  it('asks again once the memo is 30 seconds old', async () => {
    vi.useFakeTimers()
    apiGet.mockResolvedValue(payload('Week'))
    const { fetchTop } = await freshComposable()
    await fetchTop(100, { period: 'week' })

    vi.advanceTimersByTime(29_000)
    await fetchTop(100, { period: 'week' })
    expect(apiGet).toHaveBeenCalledTimes(1)

    vi.advanceTimersByTime(1_000)
    await fetchTop(100, { period: 'week' })
    expect(apiGet).toHaveBeenCalledTimes(2)
  })

  it('shares one request between two views asking the same thing', async () => {
    const pending = deferred()
    apiGet.mockReturnValue(pending.promise)
    const first = await freshComposable()
    const { useActivityLeaderboard } = await import('@/composables/portal/useActivityLeaderboard')
    const second = useActivityLeaderboard()

    const both = Promise.all([first.fetchTop(), second.fetchTop()])
    pending.resolve(payload('Month'))
    await both

    expect(apiGet).toHaveBeenCalledTimes(1)
    expect(first.entries.value[0].display_name).toBe('Month')
    expect(second.entries.value[0].display_name).toBe('Month')
  })

  it('shows the last tab clicked when an earlier answer comes after it', async () => {
    const week = deferred()
    const all = deferred()
    apiGet.mockImplementation(url => (url.includes('period=week') ? week.promise : all.promise))
    const { fetchTop, entries, stats, loading } = await freshComposable()

    const weekRequest = fetchTop(100, { period: 'week' })
    const allRequest = fetchTop(100, { period: 'all' })
    all.resolve(payload('All'))
    await allRequest
    expect(loading.value).toBe(false)
    week.resolve(payload('Week'))
    await weekRequest

    expect(entries.value[0].display_name).toBe('All')
    expect(stats.value.period_label).toBe('All')
    expect(loading.value).toBe(false)
  })

  it('stays on the last tab when it comes back to one already in its memo', async () => {
    apiGet.mockResolvedValueOnce(payload('Month'))
    const { fetchTop, entries, loading } = await freshComposable()
    await fetchTop(100, { period: 'month' })
    const week = deferred()
    apiGet.mockReturnValueOnce(week.promise)

    const weekRequest = fetchTop(100, { period: 'week' })
    expect(loading.value).toBe(true)
    await fetchTop(100, { period: 'month' })
    expect(loading.value).toBe(false)
    week.resolve(payload('Week'))
    await weekRequest

    expect(entries.value[0].display_name).toBe('Month')
    expect(loading.value).toBe(false)
  })

  it('keeps an earlier answer for when its tab is clicked again', async () => {
    const week = deferred()
    const all = deferred()
    apiGet.mockImplementation(url => (url.includes('period=week') ? week.promise : all.promise))
    const { fetchTop, entries } = await freshComposable()
    const weekRequest = fetchTop(100, { period: 'week' })
    const allRequest = fetchTop(100, { period: 'all' })
    all.resolve(payload('All'))
    week.resolve(payload('Week'))
    await Promise.all([weekRequest, allRequest])
    apiGet.mockClear()

    await fetchTop(100, { period: 'week' })

    expect(apiGet).not.toHaveBeenCalled()
    expect(entries.value[0].display_name).toBe('Week')
  })

  it('leaves the page empty after a failure, keeps nothing and asks again next time', async () => {
    apiGet.mockRejectedValueOnce({ data: { detail: 'nope' } })
    const { fetchTop, entries, error, loading } = await freshComposable()

    await fetchTop()

    expect(entries.value).toEqual([])
    expect(error.value).toBe('nope')
    expect(loading.value).toBe(false)

    apiGet.mockResolvedValueOnce(payload('Month'))
    await fetchTop()

    expect(apiGet).toHaveBeenCalledTimes(2)
    expect(entries.value[0].display_name).toBe('Month')
    expect(error.value).toBeNull()
  })

  it('ignores the failure of a tab the user has already left', async () => {
    const week = deferred()
    apiGet.mockReturnValueOnce(week.promise)
    apiGet.mockResolvedValueOnce(payload('All'))
    const { fetchTop, entries, error } = await freshComposable()

    const weekRequest = fetchTop(100, { period: 'week' })
    await fetchTop(100, { period: 'all' })
    week.reject(new Error('down'))
    await weekRequest

    expect(entries.value[0].display_name).toBe('All')
    expect(error.value).toBeNull()
  })
})
