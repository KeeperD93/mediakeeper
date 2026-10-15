/**
 * The "hide available" switch of the admin queue: only offered on the
 * all-statuses view, sent to the server there only, remembered across visits.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

const mocks = vi.hoisted(() => ({ fetchAdminRequests: vi.fn() }))

vi.mock('vue-i18n', async importOriginal => {
  const actual = await importOriginal()
  const { ref } = await import('vue')
  return { ...actual, useI18n: () => ({ t: key => key, locale: ref('fr') }) }
})
vi.mock('@/composables/portal/usePortalRequests', async () => {
  const { ref } = await import('vue')
  return {
    usePortalRequests: () => ({
      requests: ref([]),
      total: ref(0),
      fetchAdminRequests: mocks.fetchAdminRequests,
      updateRequestStatus: vi.fn(),
      deleteRequest: vi.fn(),
    }),
  }
})
vi.mock('@/composables/portal/usePortalAdmin', async () => {
  const { ref } = await import('vue')
  return { usePortalAdmin: () => ({ stats: ref(null), fetchStats: vi.fn() }) }
})
vi.mock('@/composables/useConfirm', () => ({ useConfirm: () => vi.fn() }))
vi.mock('@/composables/useToast', () => ({ useToast: () => ({ showToast: vi.fn() }) }))

import PortalRequests from '@/views/portal/PortalRequests.vue'

const KEY = 'mk_admin_requests_hide_available'

async function mountPage() {
  const w = mount(PortalRequests, {
    global: { stubs: { AdminRequestsRow: true, PortalPagination: true, RejectReasonModal: true } },
  })
  await flushPromises()
  return w
}

const toggle = w => w.find('button[role="switch"]')
const lastLoad = () => mocks.fetchAdminRequests.mock.calls.at(-1)[0]

describe('PortalRequests — hide available', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  it('hides served requests from the all-statuses view and remembers it', async () => {
    const w = await mountPage()
    expect(lastLoad().hideAvailable).toBe(false)

    await toggle(w).trigger('click')
    await flushPromises()

    expect(lastLoad().hideAvailable).toBe(true)
    expect(toggle(w).attributes('aria-checked')).toBe('true')
    expect(localStorage.getItem(KEY)).toBe('1')
  })

  it('toggles from anywhere on its pill, not only the switch', async () => {
    const w = await mountPage()

    await w.find('label.arr-switch').trigger('click')
    await flushPromises()

    expect(toggle(w).attributes('aria-checked')).toBe('true')
    expect(lastLoad().hideAvailable).toBe(true)
  })

  it('is back on at the next visit', async () => {
    localStorage.setItem(KEY, '1')

    await mountPage()

    expect(lastLoad().hideAvailable).toBe(true)
  })

  it('disappears under a status filter, which shows everything it names', async () => {
    localStorage.setItem(KEY, '1')
    const w = await mountPage()

    const availablePill = w
      .findAll('button.arr-pill')
      .find(b => b.text() === 'portal.requests.available')
    await availablePill.trigger('click')
    await flushPromises()

    expect(toggle(w).exists()).toBe(false)
    expect(lastLoad()).toMatchObject({ status: 'available', hideAvailable: false })
  })
})
