import { ref, computed } from 'vue'
import { useApi } from '@/composables/useApi'
import { useI18n } from 'vue-i18n'
import { useToast } from '@/composables/useToast'
import { TOAST_TYPE } from '@/constants/toast'
import { formatAgo as formatAgoUtil } from '@/utils/formatAgo'

export function useHealthCheck() {
  const { apiGet, apiPost } = useApi()
  const { t } = useI18n()
  const { showToast } = useToast()

  const summary = ref(null)
  const issues = ref({ items: [], total: 0, next_cursor: null, has_more: false })
  const groupedPosters = ref([])
  const scanStatus = ref({ running: false, progress: 0, total: 0, current_item: '' })
  const loading = ref(true)
  const loadingMore = ref(false)
  const filterSev = ref('')
  const filterLib = ref('')
  const filterTyp = ref('')
  const filterExt = ref('')

  let pollTimer = null

  const scoreColor = computed(() => {
    const s = summary.value?.score ?? 100
    if (s >= 80) return 'var(--color-success)'
    if (s >= 50) return 'var(--color-warning)'
    return 'var(--color-error)'
  })
  const scoreCircum = 2 * Math.PI * 52
  const scoreOffset = computed(() => {
    const s = summary.value?.score ?? 0
    return scoreCircum - (scoreCircum * s) / 100
  })
  const progressPct = computed(() => {
    if (!scanStatus.value.total) return 0
    return Math.round((scanStatus.value.progress / scanStatus.value.total) * 100)
  })
  const libOptions = computed(() =>
    Object.keys(summary.value?.by_library || {}).filter(n => n && n !== '?' && n.trim()),
  )
  const maxLibCount = computed(() => Math.max(1, ...Object.values(summary.value?.by_library || {})))
  function libPct(count) {
    return Math.round((count / maxLibCount.value) * 100)
  }
  const filteredLibraries = computed(() => {
    const bl = summary.value?.by_library || {}
    return Object.entries(bl).filter(([name]) => name && name !== '?' && name.trim() !== '')
  })

  function buildFilterParams() {
    const params = new URLSearchParams()
    if (filterSev.value) params.set('severity', filterSev.value)
    if (filterLib.value) params.set('library', filterLib.value)
    if (filterTyp.value) params.set('issue_type', filterTyp.value)
    if (filterExt.value) params.set('extension', filterExt.value)
    return params
  }

  async function loadSummary() {
    try {
      const d = await apiGet('/api/healthcheck/summary')
      if (d && d.score !== undefined) summary.value = d
    } catch {
      /* silent: healthcheck summary poll */
    }
  }

  async function loadGroupedPosters() {
    const qs = buildFilterParams().toString()
    try {
      const d = await apiGet(`/api/healthcheck/grouped${qs ? '?' + qs : ''}`)
      if (d && d.items) groupedPosters.value = d.items
    } catch {
      /* silent: grouped posters load */
    }
  }

  async function reloadIssues() {
    const params = buildFilterParams()
    params.set('limit', '50')
    try {
      const d = await apiGet(`/api/healthcheck/issues?${params}`)
      if (d) issues.value = d
    } catch {
      /* silent: issues reload */
    }
  }

  async function loadMore() {
    if (!issues.value.next_cursor || loadingMore.value) return
    loadingMore.value = true
    const params = buildFilterParams()
    params.set('limit', '50')
    params.set('cursor', issues.value.next_cursor)
    try {
      const d = await apiGet(`/api/healthcheck/issues?${params}`)
      if (d && d.items) {
        issues.value = { ...d, items: [...issues.value.items, ...d.items] }
      }
    } catch {
      /* silent: pagination load */
    }
    loadingMore.value = false
  }

  async function startScan() {
    try {
      await apiPost('/api/healthcheck/scan', {})
    } catch (e) {
      console.error('[useHealthCheck.startScan] failed to start scan', e)
      showToast(t('common.apiError.submitFailed'), TOAST_TYPE.ERR)
      return
    }
    startPolling()
  }

  async function pollStatus() {
    try {
      const d = await apiGet('/api/healthcheck/status')
      if (d) scanStatus.value = d
      if (!d?.running) {
        stopPolling()
        await loadSummary()
        await reloadIssues()
        await loadGroupedPosters()
      }
    } catch {
      /* silent: status poll retries */
    }
  }

  function startPolling() {
    stopPolling()
    pollTimer = setInterval(pollStatus, 2000)
    pollStatus()
  }
  function stopPolling() {
    if (pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }
  }

  function reloadAll() {
    reloadIssues()
    loadGroupedPosters()
  }
  function toggleSeverity(sev) {
    filterSev.value = filterSev.value === sev ? '' : sev
    filterTyp.value = ''
    reloadAll()
  }
  function toggleLibrary(lib) {
    filterLib.value = filterLib.value === lib ? '' : lib
    filterTyp.value = ''
    reloadAll()
  }
  function toggleType(typ) {
    filterTyp.value = filterTyp.value === typ ? '' : typ
    filterSev.value = ''
    reloadAll()
  }
  function toggleExt(ext) {
    filterExt.value = filterExt.value === ext ? '' : ext
    reloadAll()
  }

  const formatAgo = input => formatAgoUtil(input, t)

  return {
    summary,
    issues,
    groupedPosters,
    scanStatus,
    loading,
    loadingMore,
    filterSev,
    filterLib,
    filterTyp,
    filterExt,
    scoreColor,
    scoreCircum,
    scoreOffset,
    progressPct,
    libOptions,
    filteredLibraries,
    libPct,
    loadSummary,
    loadGroupedPosters,
    reloadIssues,
    loadMore,
    startScan,
    pollStatus,
    startPolling,
    stopPolling,
    reloadAll,
    toggleSeverity,
    toggleLibrary,
    toggleType,
    toggleExt,
    formatAgo,
  }
}
