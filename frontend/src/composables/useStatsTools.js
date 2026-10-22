import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { resolveApiError, useApi } from '@/composables/useApi'
import { useConfirm } from '@/composables/useConfirm'
import { useStats } from '@/composables/useStats'
import { useToast } from '@/composables/useToast'
import { STATS_EXCLUSION_MODE } from '@/constants/stats'
import { TOAST_TYPE } from '@/constants/toast'

// Codes the library repair answers with (200) when it cannot start.
const REPAIR_ERROR_KEYS = {
  no_active_media_source: 'stats.repair.errNoSource',
  missing_url_or_api_key: 'stats.repair.errNoConfig',
}

/**
 * Statistics → Tools tab: history import and purge, library-name repair and
 * the exclusion list. The tab only renders the state returned here.
 */
export function useStatsTools() {
  const { t } = useI18n()
  const { apiFetch, apiGet, apiPost, apiDelete } = useApi()
  const { showToast } = useToast()
  const mkConfirm = useConfirm()
  const { loadTotals } = useStats()

  const importStatus = ref(null)
  const purgeStatus = ref(null)
  const repairOpen = ref(false)
  const repairRunning = ref(false)
  const repairResult = ref(null)
  const repairError = ref('')
  const exclusions = ref([])
  const exclusionsFailed = ref(false)
  const exclMode = ref(STATS_EXCLUSION_MODE.EXACT)
  const exclValue = ref('')

  // The server's code names the failure; without one (lost connection, bare
  // status) the action's own message does. A rate limit resolves to '' (own toast).
  function failure(where, e, fallbackKey) {
    console.error(`[useStatsTools.${where}]`, e)
    return resolveApiError(e?.message, fallbackKey)
  }
  const errStatus = text => (text ? { type: TOAST_TYPE.ERR, text } : null)

  async function importJellystats(file) {
    importStatus.value = { type: TOAST_TYPE.INFO, text: t('stats.importing') }
    try {
      const fd = new FormData()
      fd.append('file', file)
      const res = await apiFetch('/api/stats/import/jellystats', { method: 'POST', body: fd })
      const d = res && (await res.json())
      importStatus.value = d && {
        type: TOAST_TYPE.OK,
        text: t('stats.importResult', {
          imported: t('stats.playsImported', d.playback_imported),
          skipped: t('stats.duplicatesIgnored', d.playback_skipped),
        }),
      }
      if (d) loadTotals()
    } catch (e) {
      importStatus.value = errStatus(
        failure('importJellystats', e, 'common.apiError.import_failed'),
      )
    }
  }

  async function purgeJellystats() {
    const ok = await mkConfirm({
      title: t('common.confirmTitle.delete'),
      message: t('stats.purgeConfirm'),
      variant: 'danger',
    })
    if (!ok) return
    purgeStatus.value = { type: TOAST_TYPE.INFO, text: t('stats.purging') }
    try {
      const d = await apiPost('/api/stats/import/jellystats/purge')
      purgeStatus.value = d && {
        type: TOAST_TYPE.OK,
        text: t('stats.playsPurged', d.total_purged),
      }
      if (d) loadTotals()
    } catch (e) {
      purgeStatus.value = errStatus(failure('purgeJellystats', e, 'common.apiError.deleteFailed'))
    }
  }

  async function repairLibraryNames() {
    repairOpen.value = true
    repairRunning.value = true
    repairResult.value = null
    repairError.value = ''
    try {
      const d = await apiPost('/api/stats/migrate/library-names')
      if (d?.error) repairError.value = t(REPAIR_ERROR_KEYS[d.error] || 'common.error')
      else repairResult.value = d
    } catch (e) {
      console.error('[useStatsTools.repairLibraryNames]', e)
      repairError.value = t('common.error')
    } finally {
      repairRunning.value = false
    }
  }

  // Add and remove answer with the whole list, so no second fetch.
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
      showToast(failure('loadExclusions', e, 'common.apiError.loadFailed'), TOAST_TYPE.ERR)
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
      showToast(failure('addExclusion', e, 'common.apiError.saveFailed'), TOAST_TYPE.ERR)
    }
  }

  async function removeExclusion(index) {
    try {
      if (setExclusions(await apiDelete(`/api/stats/exclusions/${index}`))) loadTotals()
    } catch (e) {
      showToast(failure('removeExclusion', e, 'common.apiError.deleteFailed'), TOAST_TYPE.ERR)
    }
  }

  return {
    importStatus,
    purgeStatus,
    repairOpen,
    repairRunning,
    repairResult,
    repairError,
    exclusions,
    exclusionsFailed,
    exclMode,
    exclValue,
    importJellystats,
    purgeJellystats,
    repairLibraryNames,
    loadExclusions,
    addExclusion,
    removeExclusion,
  }
}
