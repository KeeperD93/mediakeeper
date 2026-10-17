/**
 * Error messages from the API layer: a refused input (Pydantic 422) becomes
 * a code instead of "[object Object]"; resolveApiError reads a known code,
 * else the caller's own message, else a bare status as "Error 502".
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'

// Fake translations: an unknown key comes back unchanged, as with vue-i18n.
const MESSAGES = vi.hoisted(() => ({
  'common.apiError.backup_not_found': 'Backup not found.',
  'common.apiError.unknown': 'Error {status}',
  'common.apiError.deleteFailed': 'Delete failed.',
}))

vi.mock('@/i18n', () => ({
  default: {
    global: { t: (key, named) => MESSAGES[key]?.replace('{status}', named?.status) ?? key },
  },
}))
vi.mock('@/composables/apiClient', async importOriginal => ({
  ...(await importOriginal()),
  fetchApiResponse: vi.fn(),
}))

import { fetchApiResponse } from '@/composables/apiClient'
import { resolveApiError, useApi } from '@/composables/useApi'

const answer = (status, body) => ({ ok: false, status, json: async () => body })

describe('apiFetch errors', () => {
  beforeEach(() => vi.clearAllMocks())

  it('turns a refused input (422) into a code, not "[object Object]"', async () => {
    fetchApiResponse.mockResolvedValue(
      answer(422, { detail: [{ type: 'less_than_equal', loc: ['body', 'days'] }] }),
    )

    await expect(useApi().apiFetch('/api/x')).rejects.toThrow('validation_failed')
  })

  it('keeps the server code, or the status when the answer is not JSON', async () => {
    fetchApiResponse.mockResolvedValueOnce(answer(404, { detail: 'backup_not_found' }))
    await expect(useApi().apiFetch('/api/x')).rejects.toThrow('backup_not_found')

    fetchApiResponse.mockResolvedValueOnce({
      ok: false,
      status: 502,
      json: async () => {
        throw new SyntaxError('not JSON')
      },
    })
    await expect(useApi().apiFetch('/api/x')).rejects.toThrow('http_502')
  })
})

describe('resolveApiError', () => {
  it('reads a known code', () => {
    expect(resolveApiError('backup_not_found')).toBe('Backup not found.')
  })

  it("says what failed with the caller's message when the server gives no known reason", () => {
    for (const code of ['http_502', 'Failed to fetch', undefined]) {
      expect(resolveApiError(code, 'common.apiError.deleteFailed')).toBe('Delete failed.')
    }
  })

  it('reads a bare status as "Error <status>" and keeps other codes raw, without a fallback', () => {
    expect(resolveApiError('http_502')).toBe('Error 502')
    expect(resolveApiError('brand_new_code')).toBe('brand_new_code')
  })
})
