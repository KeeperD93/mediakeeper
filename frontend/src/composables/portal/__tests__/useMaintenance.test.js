import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('@/composables/useApi', () => ({
  fetchApiResponse: vi.fn(),
}))

import { fetchApiResponse } from '@/composables/useApi'
import { useMaintenance } from '@/composables/portal/useMaintenance'

function mockOk(body = { enabled: false, text: '' }) {
  fetchApiResponse.mockResolvedValue({ ok: true, json: () => Promise.resolve(body) })
}

describe('useMaintenance', () => {
  beforeEach(() => {
    const { refresh } = useMaintenance()
    refresh()
    fetchApiResponse.mockReset()
  })

  it('memoises successive calls within 30s window', async () => {
    mockOk({ enabled: true, text: 'closed' })
    const { fetchMaintenanceState } = useMaintenance()

    const first = await fetchMaintenanceState()
    const second = await fetchMaintenanceState()

    expect(first.enabled).toBe(true)
    expect(second.text).toBe('closed')
    expect(fetchApiResponse).toHaveBeenCalledTimes(1)
  })

  it('refresh() invalidates the cache so the next call hits the API again', async () => {
    mockOk({ enabled: false, text: 'a' })
    const { fetchMaintenanceState, refresh } = useMaintenance()

    await fetchMaintenanceState()
    refresh()
    mockOk({ enabled: true, text: 'b' })
    const next = await fetchMaintenanceState()

    expect(fetchApiResponse).toHaveBeenCalledTimes(2)
    expect(next.text).toBe('b')
  })

  it('force=true bypasses the memo even within the TTL window', async () => {
    mockOk({ enabled: false, text: 'cached' })
    const { fetchMaintenanceState } = useMaintenance()

    await fetchMaintenanceState()
    mockOk({ enabled: true, text: 'fresh' })
    const forced = await fetchMaintenanceState({ force: true })

    expect(fetchApiResponse).toHaveBeenCalledTimes(2)
    expect(forced.text).toBe('fresh')
  })
})
