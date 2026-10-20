import { useI18n } from 'vue-i18n'
import { resolveApiError } from '@/composables/useApi'
import { useToast } from '@/composables/useToast'
import { TOAST_TYPE } from '@/constants/toast'

/**
 * Map a media-request outcome to a user toast. Shared by the season modal
 * and the one-click movie flows so success (quota left) and refusal
 * (quota / duplicate / blacklist) feedback is identical across the portal.
 */
export function usePortalRequestFeedback() {
  const { showToast } = useToast()
  const { t } = useI18n()

  /**
   * @param result    Parsed API response (`{ success, quota, retry_count }`) or null.
   * @param errorCode Code from the thrown apiFetch error (`e.message`), if any.
   */
  function presentRequestResult(result, errorCode = null) {
    if (result?.success) {
      if (result.quota) {
        const { used, max } = result.quota
        const reached = used >= max
        showToast(
          t(reached ? 'portal.request.quotaReached' : 'portal.request.quotaInfo', { used, max }),
          reached ? TOAST_TYPE.WARN : TOAST_TYPE.OK,
          reached ? 5000 : 4000,
        )
      } else {
        const key = result.retry_count >= 1 ? 'portal.request.resubmitSuccess' : 'common.success'
        showToast(t(key), TOAST_TYPE.OK)
      }
      return
    }
    // errorCode (thrown by apiFetch) wins over res.detail/error. A refusal of
    // the portal gets its own words, another known error the shared ones;
    // anything else (no answer, bare status) says the request did not go out.
    const code = errorCode || result?.detail || result?.error
    const key = code ? `portal.request.errors.${code}` : null
    const message =
      key && t(key) !== key ? t(key) : resolveApiError(code, 'portal.request.errors.failed')
    showToast(message, TOAST_TYPE.ERR)
  }

  return { presentRequestResult }
}
