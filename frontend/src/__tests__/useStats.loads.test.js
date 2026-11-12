/**
 * Statistics loads: only the newest call of a load writes its answer, and a
 * failed load is logged and named once, the playback cards offering a retry.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { TOAST_TYPE } from '@/constants/toast'

const m = vi.hoisted(() => {
  const toasts = { value: [] }
  return {
    apiGet: vi.fn(),
    toasts,
    showToast: vi.fn((message, type) => toasts.value.push({ message, type })),
  }
})

// Every text comes back as its key.
vi.mock('@/i18n', () => ({ default: { global: { t: key => key } } }))
vi.mock('vue-i18n', () => ({ useI18n: () => ({ t: key => key }) }))
vi.mock('@/composables/useApi', async importOriginal => ({
  ...(await importOriginal()),
  useApi: () => ({ apiGet: m.apiGet }),
}))
vi.mock('@/composables/useToast', () => ({
  useToast: () => ({ toasts: m.toasts, showToast: m.showToast }),
}))

import { useStats } from '@/composables/useStats'

// A request that answers when the test says so.
function pending() {
  let resolve
  const promise = new Promise(r => (resolve = r))
  return { promise, resolve }
}
const lostConnection = () => new TypeError('Failed to fetch')

let consoleError

beforeEach(() => {
  vi.clearAllMocks()
  m.toasts.value = []
  consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
})
afterEach(() => consoleError.mockRestore())

describe('useStats — answers out of order', () => {
  it('keeps the newest period when the older one answers last', async () => {
    const s = useStats()
    const week = pending()
    const month = pending()
    m.apiGet.mockReturnValueOnce(week.promise).mockReturnValueOnce(month.promise)

    const first = s.loadPlayback(7)
    const second = s.loadPlayback(30)
    month.resolve({ period: 30 })
    await second
    week.resolve({ period: 7 })
    await first

    expect(s.playback.value).toEqual({ period: 30 })
    expect(s.loadingPlayback.value).toBe(false)
  })

  it('keeps the totals of the newest refresh and stays loading until it answers', async () => {
    const s = useStats()
    const before = pending()
    const after = pending()
    m.apiGet.mockReturnValueOnce(before.promise).mockReturnValueOnce(after.promise)

    const first = s.loadTotals()
    const second = s.loadTotals()
    before.resolve({ total_plays: 10 })
    await first
    expect(s.loadingTotals.value).toBe(true)

    after.resolve({ total_plays: 9 })
    await second
    expect(s.totals.plays).toBe(9)
    expect(s.loadingTotals.value).toBe(false)
  })
})

describe('useStats — failed loads', () => {
  it('logs each failure, names it once, and lets the playback cards retry', async () => {
    const s = useStats()
    m.apiGet.mockRejectedValue(lostConnection())

    await Promise.all([s.loadPlayback(30), s.loadTotals(), s.loadRecords()])

    expect(consoleError).toHaveBeenCalledWith('[useStats.loadPlayback]', expect.any(TypeError))
    expect(consoleError).toHaveBeenCalledWith('[useStats.loadTotals]', expect.any(TypeError))
    expect(m.showToast).toHaveBeenCalledOnce()
    expect(m.showToast).toHaveBeenCalledWith('common.apiError.loadFailed', TOAST_TYPE.ERR)
    expect(s.playback.value).toBeNull()
    expect(s.playbackFailed.value).toBe(true)

    m.apiGet.mockResolvedValueOnce({ period: 30 })
    await s.loadPlayback(30)
    expect(s.playbackFailed.value).toBe(false)
    expect(s.playback.value).toEqual({ period: 30 })
  })

  it('logs a failed sessions poll without a toast: it tries again on its own', async () => {
    const s = useStats()
    m.apiGet.mockRejectedValueOnce(lostConnection())

    await s.fetchSessions()

    expect(consoleError).toHaveBeenCalledWith('[useStats.fetchSessions]', expect.any(TypeError))
    expect(m.showToast).not.toHaveBeenCalled()
    expect(s.loadingSessions.value).toBe(false)
  })
})
