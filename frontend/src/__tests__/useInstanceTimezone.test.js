/**
 * Time zone of the instance: the status mirrors the server, a refused save keeps
 * the previous status and names what failed, an unreadable status surfaces a toast.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

const apiGet = vi.fn()
const apiPut = vi.fn()
const showToast = vi.fn()
vi.mock('@/composables/useApi', () => ({
  useApi: () => ({ apiGet, apiPut }),
  resolveApiError: (code, fallback) => (code === 'invalid_timezone' ? code : fallback),
}))
vi.mock('@/composables/useToast', () => ({ useToast: () => ({ showToast }) }))

import { useInstanceTimezone } from '@/composables/useInstanceTimezone'
import { TOAST_TYPE } from '@/constants/toast'

const ENDPOINT = '/api/system/timezone'
const STATUS = {
  timezone: null,
  effective: 'UTC',
  groups: [
    { offset: 0, zones: ['UTC'] },
    { offset: 60, zones: ['Europe/Paris'] },
  ],
}

describe('useInstanceTimezone', () => {
  let consoleError

  beforeEach(() => {
    apiGet.mockReset()
    apiPut.mockReset()
    showToast.mockClear()
    consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
  })

  afterEach(() => consoleError.mockRestore())

  it('loads the status from the server', async () => {
    apiGet.mockResolvedValue(STATUS)
    const { status, load } = useInstanceTimezone()
    await load()
    expect(apiGet).toHaveBeenCalledWith(ENDPOINT)
    expect(status.value).toEqual(STATUS)
  })

  it('names the failure when the status cannot be read', async () => {
    apiGet.mockRejectedValue(new Error('http_500'))
    const { status, load } = useInstanceTimezone()
    await load()
    expect(status.value).toBeNull()
    expect(showToast).toHaveBeenCalledWith('settings.timezoneLoadFailed', TOAST_TYPE.ERR)
  })

  it('stores the status the server returns after a save', async () => {
    const saved = { ...STATUS, timezone: 'Europe/Paris', effective: 'Europe/Paris' }
    apiPut.mockResolvedValue(saved)
    const { status, save } = useInstanceTimezone()
    await expect(save('Europe/Paris')).resolves.toBe(true)
    expect(apiPut).toHaveBeenCalledWith(ENDPOINT, { timezone: 'Europe/Paris' })
    expect(status.value).toEqual(saved)
  })

  it('reports nothing saved when the session has expired', async () => {
    apiGet.mockResolvedValue(STATUS)
    apiPut.mockResolvedValue(null)
    const { status, load, save } = useInstanceTimezone()
    await load()
    await expect(save('Europe/Paris')).resolves.toBe(false)
    expect(status.value).toEqual(STATUS)
    expect(showToast).not.toHaveBeenCalled()
  })

  it('keeps the previous status when the server refuses the zone', async () => {
    apiGet.mockResolvedValue(STATUS)
    apiPut.mockRejectedValue(new Error('invalid_timezone'))
    const { status, load, save } = useInstanceTimezone()
    await load()
    await expect(save('Mars/Olympus')).resolves.toBe(false)
    expect(status.value).toEqual(STATUS)
    expect(showToast).toHaveBeenCalledWith('invalid_timezone', TOAST_TYPE.ERR)
  })
})
