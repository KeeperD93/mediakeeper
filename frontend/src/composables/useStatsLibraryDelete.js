import { useI18n } from 'vue-i18n'
import { resolveApiError, useApi } from '@/composables/useApi'
import { useConfirm } from '@/composables/useConfirm'
import { useStats } from '@/composables/useStats'
import { useToast } from '@/composables/useToast'
import { TOAST_TYPE } from '@/constants/toast'

/**
 * Statistics → General: remove a library from the statistics after a confirm,
 * then reload the list. A failure is named in a toast.
 */
export function useStatsLibraryDelete() {
  const { t } = useI18n()
  const { apiDelete } = useApi()
  const { showToast } = useToast()
  const mkConfirm = useConfirm()
  const { loadLibraries } = useStats()

  async function deleteLibrary(id, name) {
    const ok = await mkConfirm({
      title: t('common.confirmTitle.delete'),
      message: t('stats.deleteLibConfirm', { name }),
      variant: 'danger',
      confirmLabel: t('common.delete'),
    })
    if (!ok) return
    try {
      await apiDelete(`/api/stats/libraries/${encodeURIComponent(id)}`)
      loadLibraries()
    } catch (e) {
      console.error('[useStatsLibraryDelete.deleteLibrary]', e)
      showToast(resolveApiError(e?.message, 'common.apiError.deleteFailed'), TOAST_TYPE.ERR)
    }
  }

  return { deleteLibrary }
}
