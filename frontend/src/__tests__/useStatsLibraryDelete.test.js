/**
 * Statistics → General: removing a library asks first, reloads the list once
 * removed, and names a failure instead of failing silently.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { TOAST_TYPE } from '@/constants/toast'

const m = vi.hoisted(() => ({
  apiDelete: vi.fn(),
  showToast: vi.fn(),
  confirm: vi.fn(),
  loadLibraries: vi.fn(),
}))

vi.mock('vue-i18n', () => ({ useI18n: () => ({ t: k => k }) }))
vi.mock('@/composables/useApi', () => ({
  useApi: () => ({ apiDelete: m.apiDelete }),
  resolveApiError: (code, fallbackKey) => `error:${code}|${fallbackKey}`,
}))
vi.mock('@/composables/useToast', () => ({ useToast: () => ({ showToast: m.showToast }) }))
vi.mock('@/composables/useConfirm', () => ({ useConfirm: () => m.confirm }))
vi.mock('@/composables/useStats', () => ({
  useStats: () => ({ loadLibraries: m.loadLibraries }),
}))

import { useStatsLibraryDelete } from '@/composables/useStatsLibraryDelete'

let consoleError

beforeEach(() => {
  vi.clearAllMocks()
  m.confirm.mockResolvedValue(true)
  consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
})
afterEach(() => consoleError.mockRestore())

describe('useStatsLibraryDelete', () => {
  it('does nothing when the confirm is declined', async () => {
    m.confirm.mockResolvedValue(false)
    await useStatsLibraryDelete().deleteLibrary('lib 1', 'Sample library')

    expect(m.apiDelete).not.toHaveBeenCalled()
  })

  it('removes the library, then reloads the list', async () => {
    m.apiDelete.mockResolvedValue({ ok: true })
    await useStatsLibraryDelete().deleteLibrary('lib 1', 'Sample library')

    expect(m.apiDelete).toHaveBeenCalledWith('/api/stats/libraries/lib%201')
    expect(m.loadLibraries).toHaveBeenCalledOnce()
  })

  it('names a failed removal and logs it', async () => {
    m.apiDelete.mockRejectedValue(new TypeError('Failed to fetch'))
    await useStatsLibraryDelete().deleteLibrary('lib 1', 'Sample library')

    expect(m.showToast).toHaveBeenCalledWith(
      'error:Failed to fetch|common.apiError.deleteFailed',
      TOAST_TYPE.ERR,
    )
    expect(consoleError).toHaveBeenCalledWith(
      '[useStatsLibraryDelete.deleteLibrary]',
      expect.any(TypeError),
    )
    expect(m.loadLibraries).not.toHaveBeenCalled()
  })
})
