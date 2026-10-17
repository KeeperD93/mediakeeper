/**
 * Row actions of the admin requests queue: status change (with the
 * confirmation when Emby does not hold the title), rejection with a reason,
 * deletion. One call at a time per row; the view applies the result.
 */
import { reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useConfirm } from '@/composables/useConfirm'
import { useToast } from '@/composables/useToast'
import { resolveApiError } from '@/composables/useApi'
import { TOAST_TYPE } from '@/constants/toast'
import { REQUEST_LIBRARY_ERROR, REQUEST_STATUS } from '@/constants/requests'

const LIBRARY_ERRORS = Object.values(REQUEST_LIBRARY_ERROR)

export function useAdminRequestActions({
  updateRequestStatus,
  deleteRequest,
  onStatusChanged,
  onDeleted,
}) {
  const { t } = useI18n()
  const mkConfirm = useConfirm()
  const { showToast } = useToast()

  const busyIds = reactive(new Set())
  const rejectTarget = ref(null)

  async function runExclusive(req, action) {
    if (busyIds.has(req.id)) return
    busyIds.add(req.id)
    try {
      await action()
    } finally {
      busyIds.delete(req.id)
    }
  }

  function onAction(req, newStatus) {
    if (newStatus === REQUEST_STATUS.REJECTED) {
      rejectTarget.value = req
      return
    }
    return runExclusive(req, () => applyStatus(req, newStatus, null))
  }

  function onRejectConfirm(reason) {
    const req = rejectTarget.value
    rejectTarget.value = null
    if (!req) return
    return runExclusive(req, () => applyStatus(req, REQUEST_STATUS.REJECTED, reason))
  }

  function cancelReject() {
    rejectTarget.value = null
  }

  async function applyStatus(req, newStatus, reason, force = false) {
    let res
    try {
      res = await updateRequestStatus(req.id, newStatus, reason, { force })
    } catch (e) {
      // Emby does not (verifiably) hold the title: the admin may confirm anyway.
      if (LIBRARY_ERRORS.includes(e.message)) {
        if (await confirmAvailableAnyway(req, e.message)) {
          await applyStatus(req, newStatus, reason, true)
        }
      } else {
        console.error('[PortalRequests] status update failed', e)
        showToast(resolveApiError(e.message, 'portal.admin.req.statusFailed'), TOAST_TYPE.ERR)
      }
      return
    }
    if (res?.success) {
      showToast(t('common.saved'), TOAST_TYPE.OK)
      onStatusChanged(req, newStatus, reason)
    }
  }

  function confirmAvailableAnyway(req, code) {
    const message =
      code === REQUEST_LIBRARY_ERROR.CHECK_FAILED
        ? 'portal.admin.req.libraryCheckFailed'
        : 'portal.admin.req.notInLibrary'
    return mkConfirm({
      title: t('portal.admin.req.availabilityCheckTitle'),
      message: t(message, { title: req.title }),
      variant: 'warn',
      confirmLabel: t('portal.admin.req.markAvailable'),
    })
  }

  function onDelete(req) {
    return runExclusive(req, async () => {
      const ok = await mkConfirm({
        title: t('common.confirmTitle.delete'),
        message: t('portal.admin.req.confirmDelete'),
        variant: 'danger',
        confirmLabel: t('common.delete'),
      })
      if (!ok) return
      try {
        await deleteRequest(req.id)
      } catch (e) {
        console.error('[PortalRequests] delete failed', e)
        showToast(resolveApiError(e.message, 'common.apiError.deleteFailed'), TOAST_TYPE.ERR)
        return
      }
      onDeleted(req)
    })
  }

  return { busyIds, rejectTarget, onAction, onRejectConfirm, cancelReject, onDelete }
}
