/**
 * The admin queue's server contract: `hide_available` is sent only when
 * asked for, every status change carries `force`, and a failed load
 * empties the queue before reaching the caller.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'

const mocks = vi.hoisted(() => ({
  apiGet: vi.fn(),
  apiPut: vi.fn(),
  markStatus: vi.fn(),
  invalidate: vi.fn(),
}))

vi.mock('@/composables/useApi', () => ({
  useApi: () => ({
    apiGet: mocks.apiGet,
    apiPost: vi.fn(),
    apiPut: mocks.apiPut,
    apiDelete: vi.fn(),
    loading: { value: false },
    error: { value: null },
  }),
}))
vi.mock('@/composables/portal/useRequestStatus', () => ({
  useRequestStatus: () => ({ markStatus: mocks.markStatus, invalidate: mocks.invalidate }),
}))

import { usePortalRequests } from '@/composables/portal/usePortalRequests'

describe('usePortalRequests — admin queue contract', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    mocks.apiGet.mockResolvedValue({ items: [], total: 0 })
    mocks.apiPut.mockResolvedValue({ success: true })
  })

  it('asks the server to hide served requests only when told to', async () => {
    const { fetchAdminRequests } = usePortalRequests()

    await fetchAdminRequests()
    await fetchAdminRequests({ hideAvailable: true })

    const [plain, hiding] = mocks.apiGet.mock.calls.map(
      ([url]) => new URL(url, 'http://localhost').searchParams,
    )
    expect(plain.has('hide_available')).toBe(false)
    expect(hiding.get('hide_available')).toBe('true')
  })

  it('empties the queue and lets the caller report a failed load', async () => {
    const { requests, total, fetchAdminRequests } = usePortalRequests()
    mocks.apiGet.mockResolvedValueOnce({ items: [{ id: 1 }], total: 1 })
    await fetchAdminRequests()
    mocks.apiGet.mockRejectedValueOnce(new Error('http_500'))

    await expect(fetchAdminRequests({ page: 2 })).rejects.toThrow('http_500')

    expect(requests.value).toEqual([])
    expect(total.value).toBe(0)
  })

  it('sends force with every status change', async () => {
    const { updateRequestStatus } = usePortalRequests()

    await updateRequestStatus(3, 'available')
    await updateRequestStatus(3, 'available', null, { force: true })

    expect(mocks.apiPut.mock.calls).toEqual([
      ['/api/portal/requests/3/status', { status: 'available', reason: null, force: false }],
      ['/api/portal/requests/3/status', { status: 'available', reason: null, force: true }],
    ])
  })
})
