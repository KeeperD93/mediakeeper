/**
 * Row actions of the admin requests queue: one call at a time per row,
 * rejection through the reason modal, failures that give their cause.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { TOAST_TYPE } from '@/constants/toast'

const mocks = vi.hoisted(() => ({ confirm: vi.fn(), showToast: vi.fn() }))
// Fake translations behind resolveApiError: an unknown key comes back unchanged.
const MESSAGES = vi.hoisted(() => ({ 'common.apiError.forbidden': 'Forbidden.' }))

vi.mock('vue-i18n', async importOriginal => ({
  ...(await importOriginal()),
  useI18n: () => ({ t: key => key }),
}))
vi.mock('@/i18n', () => ({ default: { global: { t: key => MESSAGES[key] ?? key } } }))
vi.mock('@/composables/useConfirm', () => ({ useConfirm: () => mocks.confirm }))
vi.mock('@/composables/useToast', () => ({ useToast: () => ({ showToast: mocks.showToast }) }))

import { useAdminRequestActions } from '@/composables/portal/useAdminRequestActions'

const rowA = { id: 1, title: 'Sample A' }
const rowB = { id: 2, title: 'Sample B' }

function setup() {
  const deps = {
    updateRequestStatus: vi.fn().mockResolvedValue({ success: true }),
    deleteRequest: vi.fn().mockResolvedValue({ success: true }),
    onStatusChanged: vi.fn(),
    onDeleted: vi.fn(),
  }
  return { deps, actions: useAdminRequestActions(deps) }
}

describe('useAdminRequestActions', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  it('runs one call at a time per row, other rows stay free', async () => {
    const { deps, actions } = setup()
    let finish
    deps.updateRequestStatus.mockReturnValueOnce(
      new Promise(resolve => {
        finish = resolve
      }),
    )

    const first = actions.onAction(rowA, 'available')
    actions.onAction(rowA, 'approved')
    await actions.onAction(rowB, 'approved')

    expect(actions.busyIds.has(rowA.id)).toBe(true)
    expect(deps.updateRequestStatus.mock.calls).toEqual([
      [1, 'available', null, { force: false }],
      [2, 'approved', null, { force: false }],
    ])

    finish({ success: true })
    await first

    expect(actions.busyIds.size).toBe(0)
    expect(deps.onStatusChanged).toHaveBeenCalledWith(rowA, 'available', null)
  })

  it('rejects through the reason modal', async () => {
    const { deps, actions } = setup()

    actions.onAction(rowA, 'rejected')
    expect(actions.rejectTarget.value).toEqual(rowA)
    expect(deps.updateRequestStatus).not.toHaveBeenCalled()

    await actions.onRejectConfirm('Not on any service')

    expect(actions.rejectTarget.value).toBeNull()
    expect(deps.updateRequestStatus).toHaveBeenCalledWith(1, 'rejected', 'Not on any service', {
      force: false,
    })
    expect(deps.onStatusChanged).toHaveBeenCalledWith(rowA, 'rejected', 'Not on any service')
  })

  it('drops the pending rejection on cancel', () => {
    const { actions } = setup()

    actions.onAction(rowA, 'rejected')
    actions.cancelReject()

    expect(actions.rejectTarget.value).toBeNull()
  })

  it('deletes only once confirmed', async () => {
    const { deps, actions } = setup()
    mocks.confirm.mockResolvedValueOnce(false).mockResolvedValueOnce(true)

    await actions.onDelete(rowA)
    expect(deps.deleteRequest).not.toHaveBeenCalled()

    await actions.onDelete(rowA)
    expect(deps.deleteRequest).toHaveBeenCalledWith(1)
    expect(deps.onDeleted).toHaveBeenCalledWith(rowA)
  })

  it('reports a failed deletion and keeps the row', async () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
    const { deps, actions } = setup()
    mocks.confirm.mockResolvedValueOnce(true)
    deps.deleteRequest.mockRejectedValueOnce(new Error('http_500'))

    await actions.onDelete(rowA)

    expect(deps.onDeleted).not.toHaveBeenCalled()
    expect(mocks.showToast).toHaveBeenCalledWith('common.apiError.deleteFailed', TOAST_TYPE.ERR)
    expect(consoleError).toHaveBeenCalledOnce()
    expect(actions.busyIds.size).toBe(0)
    consoleError.mockRestore()
  })

  it("gives the server's reason for a failed status change, else says it failed", async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
    const { deps, actions } = setup()

    deps.updateRequestStatus.mockRejectedValueOnce(new Error('forbidden'))
    await actions.onAction(rowA, 'approved')
    expect(mocks.showToast).toHaveBeenLastCalledWith('Forbidden.', TOAST_TYPE.ERR)

    deps.updateRequestStatus.mockRejectedValueOnce(new Error('http_500'))
    await actions.onAction(rowA, 'approved')
    expect(mocks.showToast).toHaveBeenLastCalledWith(
      'portal.admin.req.statusFailed',
      TOAST_TYPE.ERR,
    )
    expect(deps.onStatusChanged).not.toHaveBeenCalled()
  })
})
