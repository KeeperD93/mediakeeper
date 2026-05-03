import { ref, computed, watch, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApi } from '@/composables/useApi'

export function useLogs() {
  const { t } = useI18n()
  const { apiFetch, apiGet } = useApi()

  const files = ref([])
  const loadingFiles = ref(true)
  const debugEnabled = ref(false)

  const currentFile = ref(null)
  const rawLines = ref([])
  const search = ref('')
  const autoRefresh = ref(false)
  let refreshTimer = null

  const filters = ref({ INFO: true, DEBUG: true, WARNING: true, ERROR: true, CRITICAL: true })
  const filterModule = ref('')

  function getLevel(line) {
    const jm = line.match(/"level"\s*:\s*"(\w+)"/)
    if (jm) return jm[1]
    if (line.includes('[CRITICAL]')) return 'CRITICAL'
    if (line.includes('[ERROR]'))    return 'ERROR'
    if (line.includes('[WARNING]'))  return 'WARNING'
    if (line.includes('[DEBUG]'))    return 'DEBUG'
    return 'INFO'
  }
  function getModule(line) {
    const m = line.match(/\[mediakeeper\.([a-z_.]+)\]/) || line.match(/"logger"\s*:\s*"mediakeeper\.([a-z_.]+)"/)
    return m ? m[1] : ''
  }

  const detectedModules = computed(() => {
    const mods = new Set()
    for (const line of rawLines.value) {
      const m = line.match(/\[mediakeeper\.([a-z_.]+)\]/) || line.match(/"logger"\s*:\s*"mediakeeper\.([a-z_.]+)"/)
      if (m) mods.add(m[1])
    }
    return [...mods].sort()
  })

  const filteredLines = computed(() => {
    let lines = rawLines.value.filter(l => filters.value[getLevel(l)])
    if (filterModule.value) lines = lines.filter(l => getModule(l) === filterModule.value)
    if (search.value.trim()) {
      const q = search.value.trim().toLowerCase()
      lines = lines.filter(l => l.toLowerCase().includes(q))
    }
    return lines
  })
  const displayLines = computed(() => filteredLines.value.slice(0, 1500))

  const statusText = computed(() => {
    const total = rawLines.value.length
    const mode = autoRefresh.value ? t('logs.autoOn') : t('logs.autoOff')
    return `${total} ${t('logs.lines')} • ${mode}`
  })
  const countText = computed(() => {
    if (search.value.trim()) return `${filteredLines.value.length} ${t('logs.results', filteredLines.value.length)}`
    return `${filteredLines.value.length} / ${rawLines.value.length} ${t('logs.lines')}`
  })

  function lineClass(line) { return `log-${getLevel(line).toLowerCase()}` }

  // Returns an array of ``{ text, highlight }`` segments so the template
  // can render the line as plain text (Vue auto-escaped) with ``<mark>``
  // wrappers around the matched search term — no ``v-html`` needed.
  function lineSegments(line) {
    const q = search.value.trim()
    if (!q) return [{ text: line, highlight: false }]
    const lower = line.toLowerCase()
    const needle = q.toLowerCase()
    const out = []
    let cursor = 0
    while (cursor < line.length) {
      const found = lower.indexOf(needle, cursor)
      if (found === -1) {
        out.push({ text: line.slice(cursor), highlight: false })
        break
      }
      if (found > cursor) out.push({ text: line.slice(cursor, found), highlight: false })
      out.push({ text: line.slice(found, found + needle.length), highlight: true })
      cursor = found + needle.length
    }
    return out
  }

  async function fetchFiles() {
    loadingFiles.value = true
    try { const data = await apiGet('/api/logs/files'); if (data?.files) files.value = data.files } catch { /* silent: logs list fetch */ }
    loadingFiles.value = false
  }
  async function loadDebugMode() {
    try { const data = await apiGet('/api/logs/debug'); if (data) debugEnabled.value = data.enabled } catch { /* silent: debug flag fetch */ }
  }
  async function toggleDebug() {
    const next = !debugEnabled.value
    try { await apiFetch('/api/logs/debug', { method: 'POST', body: JSON.stringify({ enabled: next }) }); debugEnabled.value = next } catch (e) { console.warn('[useLogs.toggleDebug] failed to toggle debug flag', e) }
  }
  async function refreshContent() {
    if (!currentFile.value) return
    try { const data = await apiGet(`/api/logs/read/${encodeURIComponent(currentFile.value)}?lines=2000`); rawLines.value = data?.lines || [] } catch { /* silent: content refresh, auto-retry on next tick */ }
  }
  async function viewFile(filename) {
    currentFile.value = filename
    search.value = ''
    autoRefresh.value = false
    await refreshContent()
  }
  function backToFiles() {
    stopTimer()
    currentFile.value = null
    rawLines.value = []
    autoRefresh.value = false
  }
  async function downloadFile(filename) {
    try {
      const res = await apiFetch(`/api/logs/download/${encodeURIComponent(filename)}`)
      if (!res) return
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      document.body.appendChild(a); a.click(); a.remove()
      URL.revokeObjectURL(url)
    } catch (e) { console.warn('[useLogs.downloadFile] download failed', e) }
  }
  function toggleAutoRefresh() { autoRefresh.value = !autoRefresh.value }
  function stopTimer() { if (refreshTimer) { clearInterval(refreshTimer); refreshTimer = null } }

  watch(autoRefresh, (v) => {
    stopTimer()
    if (v && currentFile.value) refreshTimer = setInterval(() => refreshContent(), 5000)
  })

  onUnmounted(() => stopTimer())

  return {
    files, loadingFiles, debugEnabled,
    currentFile, rawLines, search, autoRefresh,
    filters, filterModule, detectedModules,
    filteredLines, displayLines, statusText, countText,
    lineClass, lineSegments,
    fetchFiles, loadDebugMode, toggleDebug, viewFile, backToFiles, downloadFile, toggleAutoRefresh,
  }
}
