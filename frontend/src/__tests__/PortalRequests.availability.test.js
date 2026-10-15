/**
 * Marking a request available while Emby does not hold the title: the
 * server answers 409, the queue asks the admin, and only a confirmation
 * resends the change with `force`.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

const mocks = vi.hoisted(() => ({
  updateRequestStatus: vi.fn(),
  confirm: vi.fn(),
  showToast: vi.fn(),
}))

vi.mock('vue-i18n', async importOriginal => {
  const actual = await importOriginal()
  const { ref } = await import('vue')
  return { ...actual, useI18n: () => ({ t: key => key, locale: ref('fr') }) }
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

async function markAvailable() {
  const w = mount(PortalRequests, {
    global: { stubs: { AdminRequestsRow: true, PortalPagination: true, RejectReasonModal: true } },
  })
  await flushPromises()
  w.findComponent(AdminRequestsRow).vm.$emit('action', 'available')
  await flushPromises()
  return w
}

describe('PortalRequests — available while missing from Emby', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('asks the admin, then forces the change once confirmed', async () => {
    mocks.updateRequestStatus
      .mockRejectedValueOnce(new Error('not_in_library'))
      .mockResolvedValueOnce({ success: true })
    mocks.confirm.mockResolvedValueOnce(true)

    await markAvailable()

    expect(mocks.confirm).toHaveBeenCalledOnce()
    expect(mocks.confirm.mock.calls[0][0].message).toBe('portal.admin.req.notInLibrary')
    expect(mocks.updateRequestStatus.mock.calls).toEqual([
      [3, 'available', null, { force: false }],
      [3, 'available', null, { force: true }],
    ])
  })

  it('leaves the request untouched when the admin cancels', async () => {
    mocks.updateRequestStatus.mockRejectedValueOnce(new Error('library_check_failed'))
    mocks.confirm.mockResolvedValueOnce(false)

    await markAvailable()

    expect(mocks.confirm.mock.calls[0][0].message).toBe('portal.admin.req.libraryCheckFailed')
    expect(mocks.updateRequestStatus).toHaveBeenCalledOnce()
  })

  it('reports any other failure in a toast instead of asking', async () => {
    mocks.updateRequestStatus.mockRejectedValueOnce(new Error('not_found'))

    await markAvailable()

    expect(mocks.confirm).not.toHaveBeenCalled()
    expect(mocks.showToast).toHaveBeenCalledOnce()
  })
})
