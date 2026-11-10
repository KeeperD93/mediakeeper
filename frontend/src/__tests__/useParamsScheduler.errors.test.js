/**
 * Scheduler tab: a change that fails says why, and an expired session stays silent.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

const h = vi.hoisted(() => ({ apiFetch: vi.fn(), showToast: vi.fn() }))

vi.mock('vue-i18n', () => ({ useI18n: () => ({ t: key => key }) }))
vi.mock('@/composables/useApi', () => ({
  useApi: () => ({ apiFetch: h.apiFetch, apiGet: vi.fn() }),
  // A rate limit resolves to nothing, its own toast says it.
  resolveApiError: (code, fallback) =>
    code === 'rate_limited_notified' ? '' : `message:${code || fallback}`,
}))
vi.mock('@/composables/useToast', () => ({ useToast: () => ({ showToast: h.showToast }) }))
vi.mock('@/utils/datetime', () => ({ localizedDateTime: () => 'date' }))

import { useParamsScheduler } from '@/composables/useParamsScheduler'
import { TOAST_TYPE } from '@/constants/toast'

const scheduler = useParamsScheduler()
const answer = body => ({ json: async () => body })
const task = () => ({ key: 'test-task', enabled: true, interval_sec: 60 })

const ACTIONS = [
  ['schedToggle', 'enabled', true],
  ['schedSaveInterval', 'interval_sec', 60],
  ['schedReset', 'interval_sec', 60],
]

describe.each(ACTIONS)('%s', (action, field, before) => {
  let consoleError

  beforeEach(() => {
    vi.clearAllMocks()
    scheduler.schedEditValues['test-task'] = { unit: 'm', amount: 2, savedSec: 60 }
    consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
  })
  afterEach(() => consoleError.mockRestore())

  it('says why when the change fails', async () => {
    const row = task()
    h.apiFetch.mockRejectedValueOnce(new Error('server_error'))
    await scheduler[action](row)
    expect(h.showToast).toHaveBeenCalledWith('message:server_error', TOAST_TYPE.ERR)
    expect(row[field]).toBe(before)
  })

  it('falls back on a generic message without a code', async () => {
    h.apiFetch.mockRejectedValueOnce(new Error(''))
    await scheduler[action](task())
    expect(h.showToast).toHaveBeenCalledWith('message:common.apiError.saveFailed', TOAST_TYPE.ERR)
  })

  it('leaves a rate limit to its own toast', async () => {
    h.apiFetch.mockRejectedValueOnce(new Error('rate_limited_notified'))
    await scheduler[action](task())
    expect(h.showToast).not.toHaveBeenCalled()
  })

  it('stays silent when the session has expired', async () => {
    const row = task()
    h.apiFetch.mockResolvedValueOnce(null)
    await scheduler[action](row)
    expect(h.showToast).not.toHaveBeenCalled()
    expect(row[field]).toBe(before)
  })

  it('confirms a change the server accepted', async () => {
    h.apiFetch.mockResolvedValueOnce(answer({ success: true, interval_sec: 120 }))
    await scheduler[action](task())
    expect(h.showToast).toHaveBeenCalledWith(expect.any(String), TOAST_TYPE.OK)
  })
})
