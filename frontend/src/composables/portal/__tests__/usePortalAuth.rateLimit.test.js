/**
 * The portal session check shows the shared rate-limit toast only when the
 * server gave no reason of its own.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'

const h = vi.hoisted(() => ({
  fetchApiResponse: vi.fn(),
  showToast: vi.fn(),
  onScreen: { value: [] },
}))

vi.mock('@/composables/useApi', () => ({
  fetchApiResponse: h.fetchApiResponse,
  useApi: () => ({ apiPut: vi.fn(), loading: { value: false }, error: { value: null } }),
}))
vi.mock('@/composables/useToast', () => ({
  useToast: () => ({ toasts: h.onScreen, showToast: h.showToast }),
}))

import { usePortalAuth } from '@/composables/portal/usePortalAuth'

const answer429 = body => ({
  ok: false,
  status: 429,
  headers: new Headers(),
  json: async () => body,
})

describe('usePortalAuth — rate limit', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    h.onScreen.value = []
  })

  it('shows the shared toast when the server gives no reason', async () => {
    h.fetchApiResponse.mockResolvedValue(answer429({ error: 'Rate limit exceeded' }))

    expect(await usePortalAuth().checkPortalAuth()).toBe(false)
    expect(h.showToast).toHaveBeenCalledTimes(1)
  })

  it("leaves the server's own reason to the caller", async () => {
    h.fetchApiResponse.mockResolvedValue(answer429({ detail: 'login_blocked' }))

    expect(await usePortalAuth().checkPortalAuth()).toBe(false)
    expect(h.showToast).not.toHaveBeenCalled()
  })
})
