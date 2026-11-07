/**
 * Router guard, portal branch, for a signed-in administrator: the portal opens
 * once a temporary password is changed. Until then the admin stays in the admin
 * shell, where the change is asked, instead of bouncing between the sign-in
 * page and the portal.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'

const ENTER_URL = '/api/portal/admin/requests/enter'
const { mustChangePassword, checkPortalAuth, fetchApiResponse } = vi.hoisted(() => ({
  mustChangePassword: { value: false },
  checkPortalAuth: vi.fn(),
  fetchApiResponse: vi.fn(),
}))

vi.mock('@/composables/useAuth', () => ({
  useAuth: () => ({
    checkAuth: async () => true,
    isAuthenticated: { value: true },
    mustChangePassword,
  }),
}))
vi.mock('@/composables/useApi', () => ({ fetchApiResponse }))
vi.mock('@/composables/portal/usePortalAuth', () => ({
  usePortalAuth: () => ({
    isPortalAuth: { value: false },
    checkPortalAuth,
    profile: { value: null },
  }),
}))
vi.mock('@/composables/portal/useMaintenance', () => ({
  useMaintenance: () => ({ fetchMaintenanceState: async () => ({ enabled: false }) }),
}))
vi.mock('@/components/layout/AppLayout.vue', () => ({ default: { template: '<div />' } }))
vi.mock('@/views/DashboardView.vue', () => ({ default: { template: '<div />' } }))
vi.mock('@/components/portal/PortalLayout.vue', () => ({ default: { template: '<div />' } }))
vi.mock('@/views/portal/PortalHome.vue', () => ({ default: { template: '<div />' } }))
vi.mock('@/views/LoginView.vue', () => ({ default: { template: '<div />' } }))

import router from '@/router'

vi.spyOn(window, 'scrollTo').mockImplementation(() => {}) // jsdom cannot scroll

function enterCalls() {
  return fetchApiResponse.mock.calls.filter(([url]) => url === ENTER_URL)
}

describe('router guard — portal entry of a signed-in admin', () => {
  beforeEach(async () => {
    checkPortalAuth.mockReset()
    fetchApiResponse.mockReset()
    await router.push('/login') // A public page: each test starts away from the portal.
  })

  it('keeps an admin with a temporary password in the admin shell', async () => {
    mustChangePassword.value = true
    checkPortalAuth.mockResolvedValue(false)

    await router.push('/portal')

    expect(router.currentRoute.value.fullPath).toBe('/')
    expect(enterCalls()).toHaveLength(0)
  })

  it('opens the portal once the password is changed', async () => {
    mustChangePassword.value = false
    checkPortalAuth.mockResolvedValueOnce(false).mockResolvedValueOnce(true)
    fetchApiResponse.mockResolvedValue({ ok: true })

    await router.push('/portal')

    expect(router.currentRoute.value.fullPath).toBe('/portal')
    expect(enterCalls()).toHaveLength(1)
  })
})
