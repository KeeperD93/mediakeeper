import { ref, reactive } from 'vue'
import { useApi } from '@/composables/useApi'
import { useToast } from '@/composables/useToast'
import { TOAST_TYPE } from '@/constants/toast'
import { TASK_STATUS } from '@/constants/scheduler'
import { useI18n } from 'vue-i18n'
import { localizedDateTime } from '@/utils/datetime'

const schedTasks = ref([])
const schedCaches = ref([])
const schedLoading = ref(false)
const schedCachesLoading = ref(false)
const schedEditValues = reactive({})
let pollTimer = null
let cachesPollTimer = null
let loadedOnce = false
let cachesLoadedOnce = false

// Cache stats refresh cadence. Short enough that the admin sees
// counters move as searches happen on the portal, long enough not
// to spam the API for a panel that's mostly observational.
const CACHES_POLL_MS = 5000

const UNITS = { s: 1, m: 60, h: 3600, d: 86400 }
function bestUnit(sec) {
  if (sec % 86400 === 0) return 'd'
  if (sec % 3600 === 0) return 'h'
  if (sec % 60 === 0) return 'm'
  return 's'
}
function intervalToAmount(sec, unit) {
  return Math.round(sec / UNITS[unit])
}
function toSeconds(amount, unit) {
  return amount * UNITS[unit]
}
function formatSeconds(sec) {
  if (sec >= 86400 && sec % 86400 === 0) return `${sec / 86400}j`
  if (sec >= 3600 && sec % 3600 === 0) return `${sec / 3600}h`
  if (sec >= 60 && sec % 60 === 0) return `${sec / 60}min`
  return `${sec}s`
}
function formatRunDate(iso) {
  if (!iso) return '—'
  return localizedDateTime(new Date(iso), {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  })
}
function schedStatusDot(task) {
  if (!task.enabled) return 'dot-off'
  if (task.last_status === TASK_STATUS.RUNNING) return 'dot-running'
  if (task.last_status === TASK_STATUS.ERROR) return 'dot-error'
  if (task.last_status === TASK_STATUS.OK) return 'dot-ok'
  return 'dot-idle'
}
function schedIsDirty(task) {
  const ev = schedEditValues[task.key]
  if (!ev) return false
  return toSeconds(ev.amount, ev.unit) !== ev.savedSec
}

export function useParamsScheduler() {
  const { apiGet, apiFetch } = useApi()
  const { showToast } = useToast()
  const { t } = useI18n()

  async function loadSched() {
    schedLoading.value = true
    try {
      const data = await apiGet('/api/scheduler/tasks')
      if (Array.isArray(data)) {
        schedTasks.value = data.map(task => ({
          ...task,
          _running: task.last_status === TASK_STATUS.RUNNING,
        }))
        schedTasks.value.forEach(task => {
          if (!schedEditValues[task.key]) {
            const unit = bestUnit(task.interval_sec)
            schedEditValues[task.key] = {
              unit,
              amount: intervalToAmount(task.interval_sec, unit),
              savedSec: task.interval_sec,
            }
          }
        })
        if (
          schedTasks.value.some(task => task.last_status === TASK_STATUS.RUNNING || task.progress)
        )
          startPolling()
      }
    } catch {
      /* silent: scheduler poll, retries on next tick */
    }
    schedLoading.value = false
    loadedOnce = true
  }

  function startPolling() {
    if (pollTimer) return
    pollTimer = setInterval(async () => {
      await loadSched()
      const anyRunning = schedTasks.value.some(
        task => task.last_status === TASK_STATUS.RUNNING || task.progress,
      )
      if (!anyRunning) stopPolling()
    }, 2000)
  }
  function stopPolling() {
    if (pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }
    if (cachesPollTimer) {
      clearInterval(cachesPollTimer)
      cachesPollTimer = null
    }
  }

  function startCachesPolling() {
    if (cachesPollTimer) return
    cachesPollTimer = setInterval(loadCaches, CACHES_POLL_MS)
  }

  async function schedToggle(task) {
    const newVal = !task.enabled
    const res = await apiFetch(`/api/scheduler/tasks/${task.key}`, {
      method: 'PATCH',
      body: JSON.stringify({ enabled: newVal }),
    })
    const data = await res.json()
    if (data.success) {
      task.enabled = newVal
      showToast(newVal ? t('scheduler.enabled') : t('scheduler.disabled'), TOAST_TYPE.OK)
    }
  }

  async function schedSaveInterval(task) {
    const ev = schedEditValues[task.key]
    if (!ev) return
    const sec = toSeconds(ev.amount, ev.unit)
    if (sec < 10) {
      showToast(t('scheduler.minInterval'), TOAST_TYPE.ERR)
      return
    }
    const res = await apiFetch(`/api/scheduler/tasks/${task.key}`, {
      method: 'PATCH',
      body: JSON.stringify({ interval_sec: sec }),
    })
    const data = await res.json()
    if (data.success) {
      task.interval_sec = sec
      ev.savedSec = sec
      showToast(t('scheduler.intervalSaved'), TOAST_TYPE.OK)
    }
  }

  async function schedReset(task) {
    const res = await apiFetch(`/api/scheduler/tasks/${task.key}/reset`, { method: 'POST' })
    const data = await res.json()
    if (data.success) {
      task.interval_sec = data.interval_sec
      const unit = bestUnit(data.interval_sec)
      schedEditValues[task.key] = {
        unit,
        amount: intervalToAmount(data.interval_sec, unit),
        savedSec: data.interval_sec,
      }
      showToast(t('scheduler.resetDone'), TOAST_TYPE.OK)
    }
  }

  async function schedRunNow(task) {
    task._running = true
    try {
      const res = await apiFetch(`/api/scheduler/tasks/${task.key}/run`, { method: 'POST' })
      const data = await res.json()
      if (data.success) {
        const label = task.label_key ? t(task.label_key, task.label) : task.label
        showToast(t('scheduler.launched', { label }), TOAST_TYPE.OK)
        setTimeout(() => {
          loadSched()
          startPolling()
        }, 1500)
      }
    } catch (e) {
      console.error('[useParamsScheduler.schedRunNow] failed to trigger task', e)
      showToast(t('common.apiError.submitFailed'), TOAST_TYPE.ERR)
    }
    setTimeout(() => {
      task._running = false
    }, 4000)
  }

  function schedOnAmountChange(key, val) {
    if (schedEditValues[key]) schedEditValues[key].amount = +val
  }
  function schedOnUnitChange(key, unit) {
    const ev = schedEditValues[key]
    if (!ev) return
    const oldSec = toSeconds(ev.amount, ev.unit)
    ev.unit = unit
    ev.amount = intervalToAmount(oldSec, unit) || 1
  }

  function ensureLoaded() {
    if (!loadedOnce) loadSched()
    if (!cachesLoadedOnce) loadCaches()
    // Keep the cache readout fresh while the tab is mounted — the
    // setInterval is cleared on unmount/deactivate via stopPolling().
    startCachesPolling()
  }

  // ── Caches ────────────────────────────────────────────────────────
  //
  // The admin panel renders one row per in-memory cache the backend
  // exposes via /api/scheduler/caches. Phase B = TMDB only. Phase C
  // will add image + DNS without changing the contract.

  async function loadCaches() {
    schedCachesLoading.value = true
    try {
      const data = await apiGet('/api/scheduler/caches')
      if (Array.isArray(data?.items)) schedCaches.value = data.items
    } catch {
      /* silent — admin readout, no toast spam */
    }
    schedCachesLoading.value = false
    cachesLoadedOnce = true
  }

  async function schedClearCache(cache) {
    try {
      const res = await apiFetch(`/api/scheduler/caches/${cache.id}/clear`, { method: 'POST' })
      const data = await res.json()
      if (data.success) {
        showToast(t('scheduler.cacheCleared', { name: cache.name }), TOAST_TYPE.OK)
        await loadCaches()
      }
    } catch (e) {
      console.error('[useParamsScheduler.schedClearCache] failed', e)
      showToast(t('common.apiError.submitFailed'), TOAST_TYPE.ERR)
    }
  }

  return {
    schedTasks,
    schedCaches,
    schedLoading,
    schedCachesLoading,
    schedEditValues,
    intervalToAmount,
    formatSeconds,
    formatRunDate,
    schedStatusDot,
    schedIsDirty,
    loadSched,
    loadCaches,
    ensureLoaded,
    startPolling,
    stopPolling,
    schedToggle,
    schedSaveInterval,
    schedReset,
    schedRunNow,
    schedClearCache,
    schedOnAmountChange,
    schedOnUnitChange,
  }
}
