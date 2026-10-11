import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApi } from '@/composables/useApi'
import { useToast } from '@/composables/useToast'
import { TOAST_TYPE } from '@/constants/toast'

const ENDPOINT = '/api/system/update-check'

// Module scope: the sidebar notice and the settings switch share one status.
const status = ref(null)
let inflight = null

/**
 * New-version check. ``status`` mirrors GET /api/system/update-check (the
 * backend caches the GitHub lookup for six hours); ``setEnabled`` flips the
 * admin switch and stores the refreshed status.
 */
export function useUpdateCheck() {
  const { apiGet, apiPut } = useApi()
  const { showToast } = useToast()
  const { t } = useI18n()

  function load() {
    inflight ??= apiGet(ENDPOINT)
      .then(data => {
        status.value = data
      })
      .catch(err => {
        // Cosmetic: without a status the sidebar simply shows no notice.
        console.error('[useUpdateCheck.load]', err)
      })
      .finally(() => {
        inflight = null
      })
    return inflight
  }

  async function setEnabled(enabled) {
    try {
      status.value = await apiPut(ENDPOINT, { enabled })
    } catch (err) {
      console.error('[useUpdateCheck.setEnabled]', err)
      showToast(t('common.networkError'), TOAST_TYPE.ERR)
    }
  }

  return { status, load, setEnabled }
}
