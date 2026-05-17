import { ref, reactive } from 'vue'
import { useApi } from '@/composables/useApi'
import { useToast } from '@/composables/useToast'
import { TOAST_TYPE } from '@/constants/toast'
import { useI18n } from 'vue-i18n'

// sessionStorage-backed module cache so duplicates count survives component
// remounts and doesn't re-hit the API on every dashboard open.
let __duplicatesCache = { loaded: false, count: '—' }
try {
  const cached =
    typeof sessionStorage !== 'undefined' ? sessionStorage.getItem('mk_duplicates_cache') : null
  if (cached) __duplicatesCache = JSON.parse(cached)
} catch {
  /* silent: corrupted sessionStorage cache → use default */
}

const MAX_HISTORY = 15

export function useDashboardData() {
  const { apiGet } = useApi()
  const { showToast } = useToast()
  const { t } = useI18n()

  const sys = reactive({ cpu: '—', cpuPct: 0, ram: '—', ramPct: 0, storage: '—', storagePct: 0 })
  const servicesList = ref([])
  const embyBaseUrl = ref('')
  const sessions = ref([])
  const allSessions = ref([])
  const logs = ref([])
  const alerts = ref([])
  const seenAlertIds = ref(new Set())
  const duplicatesCount = ref(__duplicatesCache.count)
  const watchlistLabel = ref('—')
  const watchlistScanAgo = ref('')
  const mediaStats = reactive({ plays: '—', duration: '—', storage: '—', activeUsers: '0' })
  const topUsers = ref([])
  const leaderboardEntries = ref([])
  const cpuHistory = ref([])
  const ramHistory = ref([])
  const prevSessionIds = ref(new Set())

  function playNotifSound() {
    try {
      const ctx = new (window.AudioContext || window.webkitAudioContext)()
      const osc = ctx.createOscillator()
      const gain = ctx.createGain()
      osc.connect(gain)
      gain.connect(ctx.destination)
      osc.frequency.value = 880
      osc.type = 'sine'
      gain.gain.value = 0.08
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.3)
      osc.start(ctx.currentTime)
      osc.stop(ctx.currentTime + 0.3)
    } catch {
      /* silent: AudioContext blocked by browser (no user gesture) */
    }
  }

  async function loadSystemStats() {
    try {
      const d = await apiGet('/api/stats/system')
      if (!d) return
      sys.cpu = d.cpu?.label ?? '—'
      sys.cpuPct = d.cpu?.percent ?? 0
      sys.ram = d.ram?.label ?? '—'
      sys.ramPct = d.ram?.percent ?? 0
      const fg = d.storage?.free_gb ?? 0
      sys.storagePct = d.storage?.percent ?? 0
      sys.storage = fg >= 1000 ? `${(fg / 1024).toFixed(2)} To libres` : (d.storage?.label ?? '—')
      cpuHistory.value = [...cpuHistory.value.slice(-(MAX_HISTORY - 1)), d.cpu?.percent ?? 0]
      ramHistory.value = [...ramHistory.value.slice(-(MAX_HISTORY - 1)), d.ram?.percent ?? 0]
    } catch {
      /* silent: dashboard poll, retries on next tick */
    }
  }

  async function loadServices() {
    try {
      const d = await apiGet('/api/settings/tools')
      if (!d) return
      const MEDIA_SOURCES = ['emby', 'plex', 'jellyfin']
      const list = await Promise.all(
        Object.entries(d).map(async ([k, tool]) => {
          if (!tool.enabled || !MEDIA_SOURCES.includes(k)) return null
          let online
          try {
            const p = await apiGet(`/api/settings/tools/${k}/ping`)
            online = p?.online ?? false
          } catch {
            online = false
          }
          if (k === 'emby') {
            // Prefer the optional HTTPS ``public_url`` over the internal
            // ``url`` so the dashboard "Watch on Emby" deep-link mirrors
            // what the portal builds via ``get_emby_public_url``. Falls
            // back to the internal URL when no public URL is configured.
            const pub = (tool.public_url || '').trim()
            const internal = (tool.url || '').trim()
            const chosen = pub || internal
            if (chosen) embyBaseUrl.value = chosen.replace(/\/$/, '')
          }
          return { key: k, label: tool.label || k.charAt(0).toUpperCase() + k.slice(1), online }
        }),
      )
      servicesList.value = list.filter(Boolean)
    } catch {
      /* silent: dashboard poll, retries on next tick */
    }
  }

  async function loadSessions() {
    try {
      const d = await apiGet('/api/emby/sessions')
      if (!d) return
      const all = Array.isArray(d) ? d : []
      allSessions.value = all
      const active = all.filter(s => s.is_playing || s.is_paused)
      const newIds = new Set(active.map(s => s.session_id || s.user + s.media))
      if (prevSessionIds.value.size > 0) {
        for (const s of active) {
          const sid = s.session_id || s.user + s.media
          if (!prevSessionIds.value.has(sid)) {
            showToast(
              `${s.user} is watching ${s.series || s.media || 'a media'}`,
              TOAST_TYPE.MEDIA,
              5000,
              {
                thumb: s.thumb_url || null,
                user: s.user,
                subtitle: s.episode || s.media_type || 'Now playing',
              },
            )
            playNotifSound()
          }
        }
      }
      prevSessionIds.value = newIds
      // Only update sessions if data actually changed (avoids resetting carousel timer)
      const key = s =>
        (s.session_id || s.user + s.media) +
        '|' +
        (s.is_playing ? '1' : '0') +
        '|' +
        (s.progress || 0)
      const newKey = active.map(key).join(',')
      const oldKey = sessions.value.map(key).join(',')
      if (newKey !== oldKey) sessions.value = active
    } catch {
      /* silent: dashboard poll, retries on next tick */
    }
  }

  async function loadLogs() {
    try {
      const d = await apiGet('/api/emby/logs')
      if (d) logs.value = (Array.isArray(d) ? d : []).slice(0, 50)
    } catch {
      /* silent: dashboard poll */
    }
  }
  async function loadSeenAlerts() {
    try {
      const d = await apiGet('/api/alerts/seen')
      if (d?.seen) seenAlertIds.value = new Set(d.seen.map(String))
    } catch {
      /* silent: dashboard poll */
    }
  }
  async function loadAlerts() {
    try {
      const d = await apiGet('/api/emby/alerts')
      if (d) alerts.value = Array.isArray(d) ? d : []
    } catch {
      /* silent: dashboard poll */
    }
  }

  async function loadDuplicates() {
    if (__duplicatesCache.loaded) {
      duplicatesCount.value = __duplicatesCache.count
      return
    }
    const persist = v => {
      __duplicatesCache = { loaded: true, count: v }
      try {
        sessionStorage.setItem('mk_duplicates_cache', JSON.stringify(__duplicatesCache))
      } catch {
        /* silent: sessionStorage unavailable */
      }
    }
    try {
      const d = await apiGet('/api/duplicates/count')
      const c = d?.count ?? 0
      const v = c > 0 ? String(c) : '0'
      duplicatesCount.value = v
      persist(v)
    } catch {
      duplicatesCount.value = '0'
      persist('0')
    }
  }

  async function loadWatchlist() {
    try {
      const d = await apiGet('/api/watchlist/scan/status')
      if (d?.ready) {
        const m = d.total_missing || 0
        watchlistLabel.value =
          m > 0 ? `${m} ${t('watchlist.missing').toLowerCase()}` : t('sidebar.watchlist')
        if (d.last_scan) {
          const h = Math.floor((Date.now() - new Date(d.last_scan).getTime()) / 3600000)
          watchlistScanAgo.value = h < 1 ? "il y a moins d'1h" : `il y a ${h}h`
        }
      }
    } catch {
      /* silent: dashboard poll */
    }
  }

  async function loadMediaStats() {
    try {
      const totals = await apiGet('/api/stats/totals')
      if (totals) {
        mediaStats.plays = (totals.total_plays || 0).toLocaleString(undefined)
        const h = Math.floor((totals.total_duration_ticks || 0) / 1e7 / 3600)
        mediaStats.duration = h > 0 ? h.toLocaleString(undefined) + 'h' : '—'
        mediaStats.activeUsers = String(totals.active_users_24h || 0)
        const go = (totals.total_storage_bytes || 0) / 1073741824
        mediaStats.storage =
          go >= 1000
            ? (Math.ceil((go / 1024) * 10) / 10).toFixed(1) + ' To'
            : go >= 1
              ? (Math.ceil(go * 10) / 10).toFixed(1) + ' Go'
              : '—'
      }
      const pb = await apiGet('/api/stats/playback?days=99999')
      if (pb?.top_users_hours) topUsers.value = pb.top_users_hours.slice(0, 3)
    } catch {
      /* silent: dashboard poll */
    }
  }

  async function loadLeaderboard() {
    try {
      // Backoffice-side endpoint: MK admin auth only, no Portal session
      // required. Prevents the noisy 401 and the empty-until-login widget
      // we had when we hit /api/portal/catalog/profile-full from here.
      const data = await apiGet('/api/stats/portal-monthly-leaderboard')
      leaderboardEntries.value = data?.leaderboard || []
    } catch {
      leaderboardEntries.value = []
    }
  }

  return {
    sys,
    servicesList,
    embyBaseUrl,
    sessions,
    allSessions,
    logs,
    alerts,
    seenAlertIds,
    duplicatesCount,
    watchlistLabel,
    watchlistScanAgo,
    mediaStats,
    topUsers,
    leaderboardEntries,
    cpuHistory,
    ramHistory,
    loadSystemStats,
    loadServices,
    loadSessions,
    loadLogs,
    loadSeenAlerts,
    loadAlerts,
    loadDuplicates,
    loadWatchlist,
    loadMediaStats,
    loadLeaderboard,
  }
}
