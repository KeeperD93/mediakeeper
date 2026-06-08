import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApi } from '@/composables/useApi'
import { useToast } from '@/composables/useToast'
import { TOAST_TYPE } from '@/constants/toast'
import { useConfirm } from '@/composables/useConfirm'
import { localizedDate } from '@/utils/datetime'

export function useDuplicates() {
  const { t } = useI18n()
  const { apiGet, apiFetch, apiPost } = useApi()
  const { showToast } = useToast()
  const mkConfirm = useConfirm()

  const duplicates = ref([])
  const loading = ref(true)
  const refreshing = ref(false)
  const ignoredItems = ref([])
  const history = ref([])
  const historyCursor = ref(null)
  const historyHasMore = ref(false)
  const loadingMoreHistory = ref(false)
  const historyStats = ref({ total_deleted: 0, total_bytes_freed: 0 })
  const rules = ref([])

  // Stored client-side until the backend exposes a server-tracked timestamp.
  // TODO: replace with `data.last_detection` from `/api/duplicates` once the
  //       backend persists the last successful detection run.
  const LAST_DETECTION_KEY = 'mk_doublon_last_detection'
  const RULES_STORAGE_KEY = 'mk_doublon_rules'
  const initialDetection = Number(localStorage.getItem(LAST_DETECTION_KEY))
  const lastDetection = ref(
    Number.isFinite(initialDetection) && initialDetection > 0 ? initialDetection : null,
  )

  try {
    rules.value = JSON.parse(localStorage.getItem(RULES_STORAGE_KEY) || '[]')
  } catch {
    rules.value = []
  }
  function saveRules() {
    localStorage.setItem(RULES_STORAGE_KEY, JSON.stringify(rules.value))
  }

  const ignoredKeys = computed(() => new Set(ignoredItems.value.map(i => i.key)))
  const activeDuplicates = computed(() =>
    duplicates.value.filter(d => !ignoredKeys.value.has(doubKey(d))),
  )
  function doubKey(item) {
    return `${item.id}_${item.sources.length}`
  }

  function srcScore(src) {
    let s = 0
    const h = src.height || 0
    if (h >= 2100) s += 40
    else if (h >= 1000) s += 30
    else if (h >= 700) s += 20
    else s += 5
    const codec = (src.codec || '').toUpperCase()
    if (codec.includes('HEVC') || codec.includes('H265') || codec.includes('X265')) s += 25
    else if (codec.includes('AV1')) s += 30
    else if (codec.includes('H264') || codec.includes('AVC') || codec.includes('X264')) s += 15
    else s += 5
    const mb = (src.size_bytes || 0) / 1048576
    if (mb > 5000) s += 15
    else if (mb > 2000) s += 12
    else if (mb > 500) s += 8
    else s += 3
    const br = (src.bitrate || 0) / 1000000
    if (br > 20) s += 10
    else if (br > 10) s += 7
    else if (br > 5) s += 5
    else s += 2
    return s
  }
  function bestSource(item) {
    if (!item.sources || item.sources.length < 2) return null
    return [...item.sources].sort((a, b) => srcScore(b) - srcScore(a))[0]
  }
  function isBest(item, src) {
    const b = bestSource(item)
    return b && b.path === src.path
  }
  function scoreColor(s) {
    return s >= 70
      ? 'var(--color-success)'
      : s >= 50
        ? 'var(--color-warning)'
        : 'var(--color-error)'
  }

  function formatBytes(b) {
    if (!b) return '0 Mo'
    if (b > 1073741824) return (b / 1073741824).toFixed(1) + ' Go'
    return (b / 1048576).toFixed(0) + ' Mo'
  }
  function fmtDate(d) {
    if (!d) return ''
    return localizedDate(new Date(d), {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    })
  }

  function reclaimableFor(item) {
    if (item.sources.length < 2) return '0 Mo'
    const best = bestSource(item)
    const waste = item.sources
      .filter(s => s.path !== best?.path)
      .reduce((a, s) => a + (s.size_bytes || 0), 0)
    return formatBytes(waste)
  }
  const totalReclaimable = computed(() => {
    let total = 0
    for (const item of activeDuplicates.value) {
      const best = bestSource(item)
      if (!best) continue
      total += item.sources
        .filter(s => s.path !== best.path)
        .reduce((a, s) => a + (s.size_bytes || 0), 0)
    }
    return formatBytes(total)
  })

  const rulesMatchCount = computed(() => {
    let count = 0
    for (const item of activeDuplicates.value) count += getDeleteTargets(item).length
    return count
  })
  function getDeleteTargets(item) {
    if (item.sources.length < 2 || !rules.value.length) return []
    let keep = null
    for (const rule of rules.value) {
      if (rule.field === 'keep_largest')
        keep = [...item.sources].sort((a, b) => (b.size_bytes || 0) - (a.size_bytes || 0))[0]
      else if (rule.field === 'keep_smallest')
        keep = [...item.sources].sort((a, b) => (a.size_bytes || 0) - (b.size_bytes || 0))[0]
      else if (rule.field === 'resolution' && rule.value) {
        const minH =
          rule.value === '4K'
            ? 2100
            : rule.value === '1080p'
              ? 1000
              : rule.value === '720p'
                ? 700
                : 0
        keep = [...item.sources]
          .filter(s => (s.height || 0) >= minH)
          .sort((a, b) => (b.height || 0) - (a.height || 0))[0]
      } else if (rule.field === 'codec' && rule.value) {
        const val = rule.value.toUpperCase()
        keep = item.sources.find(s => (s.codec || '').toUpperCase().includes(val))
      }
      if (keep) break
    }
    if (!keep) keep = bestSource(item)
    if (!keep) return []
    return item.sources.filter(s => s.path !== keep.path)
  }
  async function applyRules() {
    let totalDel = 0
    for (const item of [...activeDuplicates.value]) {
      const targets = getDeleteTargets(item)
      for (const src of targets) {
        if (await deleteSource(item, src, true)) totalDel++
      }
    }
    if (totalDel) showToast(t('duplicates.filesDeletedByRules', { count: totalDel }), TOAST_TYPE.OK)
  }

  let _duplicatesLastLoad = 0
  async function loadDuplicates(force = false) {
    if (!force && duplicates.value.length > 0 && Date.now() - _duplicatesLastLoad < 60000) {
      loading.value = false
      return
    }
    if (force) refreshing.value = true
    else loading.value = true
    try {
      const d = await apiGet('/api/duplicates' + (force ? '?force=true' : ''))
      if (d) {
        duplicates.value = d
        _duplicatesLastLoad = Date.now()
        // Persist the timestamp on every successful fetch (initial mount
        // included) so the label has something to show before the user
        // has clicked « Détecter ». Imprecise by ±backend-cache-TTL until
        // `data.last_detection` is exposed server-side.
        const now = Date.now()
        lastDetection.value = now
        localStorage.setItem(LAST_DETECTION_KEY, String(now))
      }
    } catch {
      showToast(t('duplicates.errorDetection'), TOAST_TYPE.ERR)
    } finally {
      loading.value = false
      if (force) {
        refreshing.value = false
        showToast(t('duplicates.detectionDone'), TOAST_TYPE.OK, 2500)
      }
    }
  }
  async function loadIgnored() {
    try {
      const d = await apiGet('/api/duplicates/ignored')
      if (Array.isArray(d)) ignoredItems.value = d
    } catch {
      /* silent: background fetch, list stays empty */
    }
  }
  // Cursor-paginated history: ``append=true`` fetches+appends the next page.
  async function loadHistory(append = false) {
    if (append && (!historyHasMore.value || loadingMoreHistory.value)) return
    if (append) loadingMoreHistory.value = true
    try {
      const params = new URLSearchParams()
      if (append && historyCursor.value) params.set('cursor', historyCursor.value)
      const d = await apiGet(`/api/duplicates/history?${params}`)
      const items = d?.items || (Array.isArray(d) ? d : [])
      history.value = append ? [...history.value, ...items] : items
      historyCursor.value = d?.next_cursor || null
      historyHasMore.value = !!d?.has_more
    } catch {
      /* silent: background fetch, list stays empty */
    } finally {
      loadingMoreHistory.value = false
    }
  }
  async function loadHistoryStats() {
    try {
      const d = await apiGet('/api/duplicates/history/stats')
      if (d) historyStats.value = d
    } catch {
      /* silent: background fetch, stats stay empty */
    }
  }

  async function ignoreDuplicate(item) {
    const key = doubKey(item)
    try {
      await apiPost('/api/duplicates/ignored/add', { keys: [key], titles: [item.title || ''] })
      ignoredItems.value.push({ key, title: item.title, ignored_at: new Date().toISOString() })
      showToast(t('duplicates.ignored'), TOAST_TYPE.OK, 2000)
    } catch {
      showToast(t('common.networkError'), TOAST_TYPE.ERR)
    }
  }
  async function restoreDuplicate(key) {
    try {
      await apiPost('/api/duplicates/ignored/remove', { keys: [key] })
      ignoredItems.value = ignoredItems.value.filter(i => i.key !== key)
      showToast(t('duplicates.restored'), TOAST_TYPE.OK, 2000)
    } catch {
      showToast(t('common.networkError'), TOAST_TYPE.ERR)
    }
  }
  async function restoreDuplicates(keys) {
    if (!keys?.length) return
    try {
      await apiPost('/api/duplicates/ignored/remove', { keys })
      const set = new Set(keys)
      ignoredItems.value = ignoredItems.value.filter(i => !set.has(i.key))
      showToast(t('duplicates.restored'), TOAST_TYPE.OK, 2000)
    } catch {
      showToast(t('common.networkError'), TOAST_TYPE.ERR)
    }
  }
  async function deleteSource(item, src, skipConfirm = false) {
    if (!skipConfirm) {
      const ok = await mkConfirm({
        title: t('common.confirmTitle.delete'),
        message: `${t('duplicates.deleteFile')}\n${src.path}`,
        variant: 'danger',
        confirmLabel: t('common.delete'),
      })
      if (!ok) return false
    }
    try {
      const res = await apiFetch('/api/media/delete', {
        method: 'POST',
        body: JSON.stringify({ path: src.path }),
      })
      const data = await res.json()
      if (data.error) {
        console.error('[useDuplicates.deleteSource] backend error', data.error)
        showToast(t('common.apiError.unknown', { status: '' }), TOAST_TYPE.ERR)
        return false
      }
      try {
        await apiPost('/api/duplicates/history/add', {
          entries: [
            {
              title: item.title,
              filename: src.name,
              size_bytes: src.size_bytes || 0,
              action: 'deleted',
            },
          ],
        })
      } catch {
        /* silent: history tracking is best-effort */
      }
      if (!skipConfirm) showToast(t('duplicates.fileDeleted'), TOAST_TYPE.OK)
      item.sources = item.sources.filter(s => s.path !== src.path)
      if (item.sources.length <= 1)
        duplicates.value = duplicates.value.filter(d => d.id !== item.id)
      historyStats.value.total_deleted++
      historyStats.value.total_bytes_freed += src.size_bytes || 0
      return true
    } catch {
      showToast(t('common.networkError'), TOAST_TYPE.ERR)
      return false
    }
  }
  async function keepSource(item, keepSrc) {
    const toDelete = item.sources.filter(s => s.path !== keepSrc.path)
    if (!toDelete.length) return
    const confirmed = await mkConfirm({
      title: t('common.confirmTitle.keepOne'),
      message: t('duplicates.keepConfirm', { n: toDelete.length }),
      variant: 'warn',
    })
    if (!confirmed) return
    let deletedCount = 0
    for (const src of toDelete) {
      if (await deleteSource(item, src, true)) deletedCount++
    }
    if (deletedCount) showToast(t('duplicates.cleaned', { n: deletedCount }), TOAST_TYPE.OK)
  }
  function refresh() {
    loadDuplicates(true)
  }

  return {
    duplicates,
    loading,
    refreshing,
    ignoredItems,
    history,
    historyHasMore,
    loadingMoreHistory,
    historyStats,
    rules,
    lastDetection,
    activeDuplicates,
    totalReclaimable,
    rulesMatchCount,
    saveRules,
    srcScore,
    bestSource,
    isBest,
    scoreColor,
    formatBytes,
    fmtDate,
    reclaimableFor,
    applyRules,
    loadDuplicates,
    loadIgnored,
    loadHistory,
    loadHistoryStats,
    ignoreDuplicate,
    restoreDuplicate,
    restoreDuplicates,
    deleteSource,
    keepSource,
    refresh,
  }
}
