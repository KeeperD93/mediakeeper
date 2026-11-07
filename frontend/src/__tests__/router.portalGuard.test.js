/**
 * Router guard, portal entry: the portal opens once a temporary password is
 * changed. Until then a signed-in admin stays in the admin shell, where the
 * change is asked, maintenance or not, instead of bouncing between the sign-in
 * page and the portal or landing on the maintenance page.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'

const ENTER_URL = '/api/portal/admin/requests/enter'
const auth = vi.hoisted(() => ({
  checkAuth: vi.fn(),
  isAuthenticated: { value: true },
  mustChangePassword: { value: false },
}))
const portal = vi.hoisted(() => ({
  checkPortalAuth: vi.fn(),
  isPortalAuth: { value: false },
  profile: { value: null },
}))
const maintenance = vi.hoisted(() => ({ enabled: false }))
const fetchApiResponse = vi.hoisted(() => vi.fn())

vi.mock('@/composables/useAuth', () => ({ useAuth: () => auth }))
vi.mock('@/composables/useApi', () => ({ fetchApiResponse }))
vi.mock('@/composables/portal/usePortalAuth', () => ({ usePortalAuth: () => portal }))
vi.mock('@/composables/portal/useMaintenance', () => ({
  useMaintenance: () => ({ fetchMaintenanceState: async () => ({ ...maintenance }) }),
}))
vi.mock('@/components/layout/AppLayout.vue', () => ({ default: { template: '<div />' } }))
vi.mock('@/views/DashboardView.vue', () => ({ default: { template: '<div />' } }))
vi.mock('@/components/portal/PortalLayout.vue', () => ({ default: { template: '<div />' } }))
vi.mock('@/views/portal/PortalHome.vue', () => ({ default: { template: '<div />' } }))
vi.mock('@/views/portal/PortalMaintenance.vue', () => ({ default: { template: '<div />' } }))
vi.mock('@/views/LoginView.vue', () => ({ default: { template: '<div />' } }))

import router from '@/router'

vi.spyOn(window, 'scrollTo').mockImplementation(() => {}) // jsdom cannot scroll

function enterCalls() {
  return fetchApiResponse.mock.calls.filter(([url]) => url === ENTER_URL)
}

describe('router guard — portal entry', () => {
  beforeEach(async () => {
    auth.checkAuth.mockReset().mockResolvedValue(true)
    auth.isAuthenticated.value = true
    auth.mustChangePassword.value = false
    portal.checkPortalAuth.mockReset().mockResolvedValue(false)
    maintenance.enabled = false
    fetchApiResponse.mockReset()
    await router.push('/login') // A public page: each test starts away from the portal.
  })

  it('keeps an admin with a temporary password in the admin shell', async () => {
    auth.mustChangePassword.value = true

    await router.push('/portal')

    expect(router.currentRoute.value.fullPath).toBe('/')
    expect(enterCalls()).toHaveLength(0)
  })

  it('opens the portal once the password is changed', async () => {
    portal.checkPortalAuth.mockResolvedValueOnce(false).mockResolvedValueOnce(true)
    fetchApiResponse.mockResolvedValue({ ok: true })

    await router.push('/portal')

    expect(router.currentRoute.value.fullPath).toBe('/portal')
    expect(enterCalls()).toHaveLength(1)
  })

  it('keeps an admin with a temporary password in the admin shell during maintenance', async () => {
    maintenance.enabled = true
    auth.mustChangePassword.value = true

    await router.push('/portal')

    expect(router.currentRoute.value.fullPath).toBe('/')
  })

  it('shows the maintenance page to a visitor without any session', async () => {
    maintenance.enabled = true
    auth.isAuthenticated.value = false
    auth.checkAuth.mockResolvedValue(false)

    await router.push('/portal')

    expect(router.currentRoute.value.name).toBe('portal-maintenance')
  })
})
