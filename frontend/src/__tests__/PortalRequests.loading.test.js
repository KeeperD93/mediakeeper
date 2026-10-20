/**
 * Loading the admin queue: the "hide available" switch (only offered on the
 * all-statuses view, sent to the server there only, remembered across
 * visits), the phone filter menus, and a failed load reported instead of an
 * empty queue.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { STORAGE_KEYS } from '@/constants/storage'
import { TOAST_TYPE } from '@/constants/toast'

const mocks = vi.hoisted(() => ({ fetchAdminRequests: vi.fn(), showToast: vi.fn() }))

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
vi.mock('@/composables/useToast', () => ({ useToast: () => ({ showToast: mocks.showToast }) }))

import PortalRequests from '@/views/portal/PortalRequests.vue'

const KEY = STORAGE_KEYS.ADMIN_REQUESTS_HIDE_AVAILABLE

async function mountPage() {
  const w = mount(PortalRequests, {
    global: { stubs: { AdminRequestsRow: true, PortalPagination: true, RejectReasonModal: true } },
  })
  await flushPromises()
  return w
}

const toggle = w => w.find('button[role="switch"]')
const lastLoad = () => mocks.fetchAdminRequests.mock.calls.at(-1)[0]

describe('PortalRequests — page', () => {
  beforeEach(() => vi.clearAllMocks())

  it('titles the page with its one h1, like the other portal pages', async () => {
    const w = await mountPage()

    expect(w.findAll('h1')).toHaveLength(1)
    expect(w.find('h1').classes()).toContain('arr-title')
  })
})

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

  it('shows everything again once switched off', async () => {
    localStorage.setItem(KEY, '1')
    const w = await mountPage()

    await toggle(w).trigger('click')
    await flushPromises()

    expect(lastLoad().hideAvailable).toBe(false)
    expect(localStorage.getItem(KEY)).toBe('0')
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

describe('PortalRequests — phone filter menus', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  it('reload the queue like the pills', async () => {
    const w = await mountPage()

    await w.find('select[aria-label="portal.admin.req.statusFilterLabel"]').setValue('pending')
    await flushPromises()
    expect(lastLoad()).toMatchObject({ status: 'pending', mediaType: null })

    await w.find('select[aria-label="portal.admin.req.typeFilterLabel"]').setValue('movie')
    await flushPromises()
    expect(lastLoad()).toMatchObject({ status: 'pending', mediaType: 'movie', page: 1 })
  })

  it('give the sort menu the shared chevron too', async () => {
    const w = await mountPage()

    const sort = w.find('select[aria-label="portal.admin.req.sortLabel"]')
    expect(sort.classes()).toContain('mk-select-chevron')
  })
})

describe('PortalRequests — failed load', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  it('reports it in an error toast and the console', async () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
    mocks.fetchAdminRequests.mockRejectedValueOnce(new Error('http_500'))

    const w = await mountPage()

    expect(mocks.showToast).toHaveBeenCalledWith('common.apiError.loadFailed', TOAST_TYPE.ERR)
    expect(consoleError).toHaveBeenCalledOnce()
    expect(w.find('.arr-loading').exists()).toBe(false)
    consoleError.mockRestore()
  })
})
