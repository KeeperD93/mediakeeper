/**
 * Statistics exclusions: the list is taken from the add / remove answers (no
 * second fetch), a failure says which action failed, and a list that failed
 * to load stays flagged until a retry succeeds.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { TOAST_TYPE } from '@/constants/toast'

const m = vi.hoisted(() => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  apiDelete: vi.fn(),
  showToast: vi.fn(),
  loadTotals: vi.fn(),
}))

// Every text comes back as its key.
vi.mock('@/i18n', () => ({ default: { global: { t: key => key } } }))
vi.mock('@/composables/useApi', async importOriginal => ({
  ...(await importOriginal()),
  useApi: () => ({ apiGet: m.apiGet, apiPost: m.apiPost, apiDelete: m.apiDelete }),
}))
vi.mock('@/composables/useToast', () => ({ useToast: () => ({ showToast: m.showToast }) }))
vi.mock('@/composables/useStats', () => ({ useStats: () => ({ loadTotals: m.loadTotals }) }))

import { useStatsExclusions } from '@/composables/useStatsExclusions'

const LIST = [{ mode: 'contains', value: 'Trailer' }]
const lostConnection = () => new TypeError('Failed to fetch')

let consoleError

beforeEach(() => {
  vi.clearAllMocks()
  consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
})
afterEach(() => consoleError.mockRestore())

describe('useStatsExclusions', () => {
  it('loads the list', async () => {
    m.apiGet.mockResolvedValue(LIST)
    const s = useStatsExclusions()
    await s.loadExclusions()
    expect(m.apiGet).toHaveBeenCalledWith('/api/stats/exclusions')
    expect(s.exclusions.value).toEqual(LIST)
    expect(s.exclusionsFailed.value).toBe(false)
  })

  it('flags a list that failed to load, says so, and clears the flag on a retry', async () => {
    const s = useStatsExclusions()
    m.apiGet.mockRejectedValueOnce(lostConnection())
    await s.loadExclusions()
    expect(s.exclusionsFailed.value).toBe(true)
    expect(m.showToast).toHaveBeenCalledWith('common.apiError.loadFailed', TOAST_TYPE.ERR)
    expect(consoleError).toHaveBeenCalledWith(
      '[useStatsExclusions.loadExclusions]',
      expect.any(TypeError),
    )

    m.apiGet.mockResolvedValueOnce(LIST)
    await s.loadExclusions()
    expect(s.exclusionsFailed.value).toBe(false)
    expect(s.exclusions.value).toEqual(LIST)
  })

  it('adds a trimmed title and takes the list from the answer', async () => {
    m.apiPost.mockResolvedValue(LIST)
    const s = useStatsExclusions()
    s.exclMode.value = 'contains'
    s.exclValue.value = '  Trailer '
    await s.addExclusion()
    expect(m.apiPost).toHaveBeenCalledWith('/api/stats/exclusions', {
      mode: 'contains',
      value: 'Trailer',
    })
    expect(m.apiGet).not.toHaveBeenCalled()
    expect(s.exclusions.value).toEqual(LIST)
    expect(s.exclValue.value).toBe('')
    expect(m.loadTotals).toHaveBeenCalledOnce()
  })

  it('ignores a blank title', async () => {
    const s = useStatsExclusions()
    s.exclValue.value = '   '
    await s.addExclusion()
    expect(m.apiPost).not.toHaveBeenCalled()
  })

  it('changes nothing when the session expired (no answer)', async () => {
    m.apiPost.mockResolvedValue(null)
    m.apiDelete.mockResolvedValue(null)
    const s = useStatsExclusions()
    s.exclValue.value = 'Trailer'
    await s.addExclusion()
    await s.removeExclusion(0)
    expect(s.exclusions.value).toEqual([])
    expect(s.exclValue.value).toBe('Trailer')
    expect(m.loadTotals).not.toHaveBeenCalled()
  })

  it('keeps the typed title and says the add failed', async () => {
    m.apiPost.mockRejectedValue(lostConnection())
    const s = useStatsExclusions()
    s.exclValue.value = 'Trailer'
    await s.addExclusion()
    expect(s.exclValue.value).toBe('Trailer')
    expect(m.showToast).toHaveBeenCalledWith('common.apiError.saveFailed', TOAST_TYPE.ERR)
    expect(consoleError).toHaveBeenCalledWith(
      '[useStatsExclusions.addExclusion]',
      expect.any(TypeError),
    )
  })

  it('removes by position and says when it failed', async () => {
    const s = useStatsExclusions()
    m.apiDelete.mockResolvedValueOnce([])
    await s.removeExclusion(0)
    expect(m.apiDelete).toHaveBeenCalledWith('/api/stats/exclusions/0')
    expect(s.exclusions.value).toEqual([])
    expect(m.loadTotals).toHaveBeenCalledOnce()

    m.apiDelete.mockRejectedValueOnce(lostConnection())
    await s.removeExclusion(0)
    expect(m.showToast).toHaveBeenCalledWith('common.apiError.deleteFailed', TOAST_TYPE.ERR)
    expect(consoleError).toHaveBeenCalledWith(
      '[useStatsExclusions.removeExclusion]',
      expect.any(TypeError),
    )
  })
})
