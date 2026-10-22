/**
 * Statistics tools: each action reports its own result, a failure gives the
 * server's reason or else says which action failed (never the browser's own
 * text), and a rate limit leaves only its toast.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { TOAST_TYPE } from '@/constants/toast'

const m = vi.hoisted(() => ({
  apiFetch: vi.fn(),
  apiPost: vi.fn(),
  loadTotals: vi.fn(),
  confirm: vi.fn(),
}))
// The few texts these checks read; any other key comes back as is.
const MESSAGES = vi.hoisted(() => ({
  'common.apiError.import_invalid_json': 'Invalid JSON file',
  'stats.importResult': '{imported}, {skipped}',
  'stats.playsImported': '{n} imported',
  'stats.duplicatesIgnored': '{n} skipped',
  'stats.playsPurged': '{n} deleted',
}))
const render = (key, named = {}) =>
  (MESSAGES[key] ?? key).replace(/\{(\w+)\}/g, (_, name) => named[name])

vi.mock('@/i18n', () => ({ default: { global: { t: (key, named) => render(key, named) } } }))
vi.mock('vue-i18n', () => ({
  // As in vue-i18n: t(key), t(key, named) or t(key, n), where n also fills {n}.
  useI18n: () => ({ t: (key, a) => render(key, typeof a === 'number' ? { n: a } : a) }),
}))
vi.mock('@/composables/useApi', async importOriginal => ({
  ...(await importOriginal()),
  useApi: () => ({
    apiFetch: m.apiFetch,
    apiPost: m.apiPost,
  }),
}))
vi.mock('@/composables/useConfirm', () => ({ useConfirm: () => m.confirm }))
vi.mock('@/composables/useStats', () => ({ useStats: () => ({ loadTotals: m.loadTotals }) }))

import { useStatsTools } from '@/composables/useStatsTools'

const file = () => new File(['{}'], 'history.json', { type: 'application/json' })
const answer = body => ({ json: async () => body })
const lostConnection = () => new TypeError('Failed to fetch')

let consoleError

beforeEach(() => {
  vi.clearAllMocks()
  consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
  m.confirm.mockResolvedValue(true)
})
afterEach(() => consoleError.mockRestore())

describe('useStatsTools — history import', () => {
  it('sends the file, reports the counts and refreshes the totals', async () => {
    m.apiFetch.mockResolvedValue(answer({ playback_imported: 12, playback_skipped: 3 }))
    const s = useStatsTools()
    const done = s.importJellystats(file())
    expect(s.importStatus.value).toEqual({ type: TOAST_TYPE.INFO, text: 'stats.importing' })
    await done

    const [url, opts] = m.apiFetch.mock.calls[0]
    expect(url).toBe('/api/stats/import/jellystats')
    expect(opts.method).toBe('POST')
    expect(opts.body.get('file').name).toBe('history.json')
    expect(s.importStatus.value).toEqual({ type: TOAST_TYPE.OK, text: '12 imported, 3 skipped' })
    expect(m.loadTotals).toHaveBeenCalledOnce()
  })

  it("names the server's reason, else the failed import", async () => {
    const s = useStatsTools()
    m.apiFetch.mockRejectedValueOnce(new Error('import_invalid_json'))
    await s.importJellystats(file())
    expect(s.importStatus.value).toEqual({ type: TOAST_TYPE.ERR, text: 'Invalid JSON file' })

    m.apiFetch.mockRejectedValueOnce(lostConnection())
    await s.importJellystats(file())
    expect(s.importStatus.value.text).toBe('common.apiError.import_failed')
    expect(consoleError).toHaveBeenCalledWith(
      '[useStatsTools.importJellystats]',
      expect.any(TypeError),
    )
  })

  it('shows nothing when the session expired (no answer)', async () => {
    m.apiFetch.mockResolvedValue(null)
    const s = useStatsTools()
    await s.importJellystats(file())
    expect(s.importStatus.value).toBeNull()
    expect(m.loadTotals).not.toHaveBeenCalled()
  })

  it('leaves only the rate-limit toast', async () => {
    m.apiFetch.mockRejectedValue(new Error('rate_limited_notified'))
    const s = useStatsTools()
    await s.importJellystats(file())
    expect(s.importStatus.value).toBeNull()
  })
})

describe('useStatsTools — purge', () => {
  it('does nothing when the confirm is declined', async () => {
    m.confirm.mockResolvedValue(false)
    const s = useStatsTools()
    await s.purgeJellystats()
    expect(m.apiPost).not.toHaveBeenCalled()
    expect(s.purgeStatus.value).toBeNull()
  })

  it('reports the purged count and refreshes the totals', async () => {
    m.apiPost.mockResolvedValue({ total_purged: 42 })
    const s = useStatsTools()
    await s.purgeJellystats()
    expect(m.apiPost).toHaveBeenCalledWith('/api/stats/import/jellystats/purge')
    expect(s.purgeStatus.value).toEqual({ type: TOAST_TYPE.OK, text: '42 deleted' })
    expect(m.loadTotals).toHaveBeenCalledOnce()
  })

  it('shows nothing when the session expired (no answer)', async () => {
    m.apiPost.mockResolvedValue(null)
    const s = useStatsTools()
    await s.purgeJellystats()
    expect(s.purgeStatus.value).toBeNull()
    expect(m.loadTotals).not.toHaveBeenCalled()
  })

  it('says the purge failed, or leaves only the rate-limit toast', async () => {
    const s = useStatsTools()
    m.apiPost.mockRejectedValueOnce(lostConnection())
    await s.purgeJellystats()
    expect(s.purgeStatus.value).toEqual({
      type: TOAST_TYPE.ERR,
      text: 'common.apiError.deleteFailed',
    })
    expect(consoleError).toHaveBeenCalledWith(
      '[useStatsTools.purgeJellystats]',
      expect.any(TypeError),
    )

    m.apiPost.mockRejectedValueOnce(new Error('rate_limited_notified'))
    await s.purgeJellystats()
    expect(s.purgeStatus.value).toBeNull()
  })
})

describe('useStatsTools — library repair', () => {
  it.each([
    ['no_active_media_source', 'stats.repair.errNoSource'],
    ['missing_url_or_api_key', 'stats.repair.errNoConfig'],
    ['something_else', 'common.error'],
  ])('explains a %s answer', async (code, key) => {
    m.apiPost.mockResolvedValue({ error: code })
    const s = useStatsTools()
    await s.repairLibraryNames()
    expect(s.repairOpen.value).toBe(true)
    expect(s.repairError.value).toBe(key)
    expect(s.repairResult.value).toBeNull()
    expect(s.repairRunning.value).toBe(false)
  })

  it('shows the result, and an error when the call fails', async () => {
    const s = useStatsTools()
    m.apiPost.mockResolvedValueOnce({ candidates: 2, migrated: 1, unresolved: 1, errors: 0 })
    await s.repairLibraryNames()
    expect(s.repairResult.value.migrated).toBe(1)
    expect(s.repairError.value).toBe('')

    m.apiPost.mockRejectedValueOnce(new Error('http_500'))
    await s.repairLibraryNames()
    expect(s.repairResult.value).toBeNull()
    expect(s.repairError.value).toBe('common.error')
    expect(s.repairRunning.value).toBe(false)
    expect(consoleError).toHaveBeenCalledWith(
      '[useStatsTools.repairLibraryNames]',
      expect.any(Error),
    )
  })
})
