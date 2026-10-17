/**
 * Marking a request available while Emby does not hold the title: the
 * server answers 409, the queue asks the admin, and only a confirmation
 * resends the change with `force`. The row stays locked while it runs.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { TOAST_TYPE } from '@/constants/toast'

const mocks = vi.hoisted(() => ({
  updateRequestStatus: vi.fn(),
  confirm: vi.fn(),
  showToast: vi.fn(),
}))

vi.mock('vue-i18n', async importOriginal => {
  const actual = await importOriginal()
  const { ref } = await import('vue')
  // Keeps the title parameter visible so the confirmation text is checked too.
  const t = (key, params) => (params?.title ? `${key}|${params.title}` : key)
  return { ...actual, useI18n: () => ({ t, locale: ref('fr') }) }
})
vi.mock('@/composables/portal/usePortalRequests', async () => {
  const { ref } = await import('vue')
  return {
    usePortalRequests: () => ({
      requests: ref([
        { id: 3, tmdb_id: 9, media_type: 'movie', title: 'Sample', status: 'approved' },
      ]),
      total: ref(1),
      fetchAdminRequests: vi.fn(),
      updateRequestStatus: mocks.updateRequestStatus,
      deleteRequest: vi.fn(),
    }),
  }
})
vi.mock('@/composables/portal/usePortalAdmin', async () => {
  const { ref } = await import('vue')
  return { usePortalAdmin: () => ({ stats: ref(null), fetchStats: vi.fn() }) }
})
vi.mock('@/composables/useConfirm', () => ({ useConfirm: () => mocks.confirm }))
vi.mock('@/composables/useToast', () => ({ useToast: () => ({ showToast: mocks.showToast }) }))

import PortalRequests from '@/views/portal/PortalRequests.vue'
import AdminRequestsRow from '@/components/portal/admin/AdminRequestsRow.vue'

const HIDE_AVAILABLE_KEY = 'mk_admin_requests_hide_available'

async function mountQueue() {
  const w = mount(PortalRequests, {
    global: { stubs: { AdminRequestsRow: true, PortalPagination: true, RejectReasonModal: true } },
  })
  await flushPromises()
  return w
}

async function markAvailable() {
  const w = await mountQueue()
  w.findComponent(AdminRequestsRow).vm.$emit('action', 'available')
  await flushPromises()
  return w
}

describe('PortalRequests — available while missing from Emby', () => {
  beforeEach(() => {
    // resetAllMocks also drops queued *Once values a failing test left behind.
    vi.resetAllMocks()
    localStorage.clear()
  })

  it('asks the admin, then forces the change once confirmed', async () => {
    mocks.updateRequestStatus
      .mockRejectedValueOnce(new Error('not_in_library'))
      .mockResolvedValueOnce({ success: true })
    mocks.confirm.mockResolvedValueOnce(true)

    await markAvailable()

    expect(mocks.confirm).toHaveBeenCalledOnce()
    expect(mocks.confirm.mock.calls[0][0].message).toBe('portal.admin.req.notInLibrary|Sample')
    expect(mocks.updateRequestStatus.mock.calls).toEqual([
      [3, 'available', null, { force: false }],
      [3, 'available', null, { force: true }],
    ])
  })

  it('leaves the request untouched when the admin cancels', async () => {
    mocks.updateRequestStatus.mockRejectedValueOnce(new Error('library_check_failed'))
    mocks.confirm.mockResolvedValueOnce(false)

    const w = await markAvailable()

    expect(mocks.confirm.mock.calls[0][0].message).toBe(
      'portal.admin.req.libraryCheckFailed|Sample',
    )
    expect(mocks.updateRequestStatus).toHaveBeenCalledOnce()
    expect(w.findComponent(AdminRequestsRow).props('req').status).toBe('approved')
    expect(mocks.showToast).not.toHaveBeenCalled()
  })

  it('reports any other failure in an error toast and the console instead of asking', async () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
    mocks.updateRequestStatus.mockRejectedValueOnce(new Error('not_found'))

    await markAvailable()

    expect(mocks.confirm).not.toHaveBeenCalled()
    expect(mocks.showToast).toHaveBeenCalledWith(expect.any(String), TOAST_TYPE.ERR)
    expect(consoleError).toHaveBeenCalledOnce()
    consoleError.mockRestore()
  })

  it('drops the row at once when served requests are hidden', async () => {
    localStorage.setItem(HIDE_AVAILABLE_KEY, '1')
    mocks.updateRequestStatus.mockResolvedValueOnce({ success: true })

    const w = await markAvailable()

    expect(w.findAllComponents(AdminRequestsRow)).toHaveLength(0)
  })

  it('locks the row while its change runs, so a second click does nothing', async () => {
    let finish
    mocks.updateRequestStatus.mockReturnValueOnce(
      new Promise(resolve => {
        finish = resolve
      }),
    )
    const w = await mountQueue()
    const row = w.findComponent(AdminRequestsRow)

    row.vm.$emit('action', 'available')
    row.vm.$emit('action', 'approved')
    await flushPromises()

    expect(row.props('busy')).toBe(true)
    expect(mocks.updateRequestStatus).toHaveBeenCalledOnce()

    finish({ success: true })
    await flushPromises()

    expect(row.props('busy')).toBe(false)
    expect(row.props('req').status).toBe('available')
  })
})
