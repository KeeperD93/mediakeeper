/**
 * Covers the shared new-version status: concurrent loads share one request,
 * a failed load leaves no status, the switch stores the refreshed status, and
 * a failed save keeps the previous status and surfaces a toast.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

const apiGet = vi.fn()
const apiPut = vi.fn()
const showToast = vi.fn()
vi.mock('@/composables/useApi', () => ({ useApi: () => ({ apiGet, apiPut }) }))
vi.mock('@/composables/useToast', () => ({ useToast: () => ({ showToast }) }))
vi.mock('vue-i18n', () => ({ useI18n: () => ({ t: k => k }) }))

const ENDPOINT = '/api/system/update-check'
const STATUS = {
  enabled: true,
  locked: false,
  current_version: '1.0.0',
  latest_version: '1.0.1',
  update_available: true,
  release_url: 'https://github.com/KeeperD93/mediakeeper/releases/tag/v1.0.1',
}

// The status lives at module scope: re-import for a clean slate per test.
async function freshUpdateCheck() {
  vi.resetModules()
  const { useUpdateCheck } = await import('@/composables/useUpdateCheck')
  return useUpdateCheck()
}

describe('useUpdateCheck', () => {
  let consoleError

  beforeEach(() => {
    apiGet.mockReset()
    apiPut.mockReset()
    showToast.mockClear()
    consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
  })

  afterEach(() => {
    consoleError.mockRestore()
  })

  it('shares one request between concurrent loads', async () => {
    apiGet.mockResolvedValue(STATUS)
    const { status, load } = await freshUpdateCheck()
    await Promise.all([load(), load()])
    expect(apiGet).toHaveBeenCalledTimes(1)
    expect(apiGet).toHaveBeenCalledWith(ENDPOINT)
    expect(status.value).toEqual(STATUS)
  })

  it('keeps no status when the check cannot be loaded', async () => {
    apiGet.mockRejectedValue(new Error('http_500'))
    const { status, load } = await freshUpdateCheck()
    await load()
    expect(status.value).toBeNull()
    expect(consoleError).toHaveBeenCalled()
  })

  it('stores the refreshed status after a switch change', async () => {
    apiPut.mockResolvedValue({ ...STATUS, enabled: false, update_available: false })
    const { status, setEnabled } = await freshUpdateCheck()
    await setEnabled(false)
    expect(apiPut).toHaveBeenCalledWith(ENDPOINT, { enabled: false })
    expect(status.value.enabled).toBe(false)
  })

  it('keeps the previous status and shows a toast when saving fails', async () => {
    apiGet.mockResolvedValue(STATUS)
    apiPut.mockRejectedValue(new Error('http_500'))
    const { status, load, setEnabled } = await freshUpdateCheck()
    await load()
    await setEnabled(false)
    expect(status.value).toEqual(STATUS)
    expect(showToast).toHaveBeenCalledWith('common.networkError', expect.anything())
  })
})
