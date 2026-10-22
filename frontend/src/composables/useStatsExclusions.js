import { ref } from 'vue'
import { resolveApiError, useApi } from '@/composables/useApi'
import { useStats } from '@/composables/useStats'
import { useToast } from '@/composables/useToast'
import { STATS_EXCLUSION_MODE } from '@/constants/stats'
import { TOAST_TYPE } from '@/constants/toast'

/**
 * Statistics → Tools: the titles hidden from the statistics. Add and remove
 * answer with the whole list, so no second fetch; a failure is named.
 */
export function useStatsExclusions() {
  const { apiGet, apiPost, apiDelete } = useApi()
  const { showToast } = useToast()
  const { loadTotals } = useStats()

  const exclusions = ref([])
  const exclusionsFailed = ref(false)
  const exclMode = ref(STATS_EXCLUSION_MODE.EXACT)
  const exclValue = ref('')

  // The server's code names the failure; without one (lost connection, bare
  // status) the action's own message does.
  function fail(where, e, fallbackKey) {
    console.error(`[useStatsExclusions.${where}]`, e)
    showToast(resolveApiError(e?.message, fallbackKey), TOAST_TYPE.ERR)
  }

  function setExclusions(list) {
    if (!Array.isArray(list)) return false
    exclusions.value = list
    exclusionsFailed.value = false
    return true
  }

  async function loadExclusions() {
    try {
      setExclusions(await apiGet('/api/stats/exclusions'))
    } catch (e) {
      exclusionsFailed.value = true
      fail('loadExclusions', e, 'common.apiError.loadFailed')
    }
  }

  async function addExclusion() {
    const value = exclValue.value.trim()
    if (!value) return
    try {
      if (!setExclusions(await apiPost('/api/stats/exclusions', { mode: exclMode.value, value })))
        return
      exclValue.value = ''
      loadTotals()
    } catch (e) {
      fail('addExclusion', e, 'common.apiError.saveFailed')
    }
  }

  async function removeExclusion(index) {
    try {
      if (setExclusions(await apiDelete(`/api/stats/exclusions/${index}`))) loadTotals()
    } catch (e) {
      fail('removeExclusion', e, 'common.apiError.deleteFailed')
    }
  }

  return {
    exclusions,
    exclusionsFailed,
    exclMode,
    exclValue,
    loadExclusions,
    addExclusion,
    removeExclusion,
  }
}
