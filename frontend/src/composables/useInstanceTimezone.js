import { ref } from 'vue'
import { resolveApiError, useApi } from '@/composables/useApi'
import { useToast } from '@/composables/useToast'
import { TOAST_TYPE } from '@/constants/toast'

const ENDPOINT = '/api/system/timezone'

/**
 * Time zone of the instance. ``status`` mirrors GET /api/system/timezone: the
 * saved zone (or null), the zone in use and the zones to choose from.
 */
export function useInstanceTimezone() {
  const { apiGet, apiPut } = useApi()
  const { showToast } = useToast()
  const status = ref(null)

  async function load() {
    try {
      status.value = await apiGet(ENDPOINT)
    } catch (err) {
      console.error('[useInstanceTimezone.load]', err)
      showToast(resolveApiError(err.message, 'settings.timezoneLoadFailed'), TOAST_TYPE.ERR)
    }
  }

  /** Returns whether the zone was saved; a refused zone keeps the previous status. */
  async function save(timezone) {
    try {
      // Nothing comes back when the session has expired and the page redirects.
      const saved = await apiPut(ENDPOINT, { timezone })
      if (!saved) return false
      status.value = saved
      return true
    } catch (err) {
      console.error('[useInstanceTimezone.save]', err)
      showToast(resolveApiError(err.message, 'settings.timezoneSaveFailed'), TOAST_TYPE.ERR)
      return false
    }
  }

  return { status, load, save }
}
