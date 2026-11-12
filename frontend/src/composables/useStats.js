import { ref, reactive } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApi } from './useApi'
import { useStatsLoadRunner } from './useStatsLoadRunner'
import {
  ticksToTime,
  ticksToHours,
  fmtSize,
  langLabel,
  langShort,
  parseTicks,
} from '@/utils/statsFormat'

/* Module-level state — shared across all useStats() callers so tab
 * components in StatsView see the same refs (totals loaded by GeneralTab
 * are visible to TotalsRow, etc.). Before hoisting, each call created
 * isolated refs and sub-components never saw loaded data. */
const totals = reactive({
  plays: 0,
  duration: 0,
  users24h: 0,
  transcodePct: 0,
  storageBytes: 0,
  totalUsers: 0,
  disabledUsers: 0,
})
const sessions = ref([])
const playback = ref(null)
const libraries = ref([])
const sparklinePlays = ref([])
const sparklineDuration = ref([])
const records = ref(null)
const userProfile = ref(null)
const users = ref({ users: [], total: 0, page: 1, per_page: 30 })
const activity = ref({ items: [], total: 0, limit: 25, next_cursor: null, has_more: false })
const activityUsers = ref([]) // distinct users in the activity history (display filter)
const minimap24h = ref([])
const dailyChart = ref(null)
const heatmap = ref(null)

const loadingTotals = ref(false)
const loadingSessions = ref(false)
const loadingPlayback = ref(false)
const loadingLibraries = ref(false)
const loadingUsers = ref(false)
const loadingActivity = ref(false)
const loadingChart = ref(false)
const loadingHeatmap = ref(false)
const playbackFailed = ref(false)

const sessionPositions = reactive({})
let tickTimer = null
let pollTimer = null
let sessionInitialLoad = true
const seriesImageCache = {}

function getSessionProgress(session) {
  const k = session.user_id + '_' + session.media,
    c = sessionPositions[k]
  if (!c || !c.dt)
    return { position: session.position, duration: session.duration, pct: session.progress }
  const now = Date.now(),
    pos = c.playing ? Math.min(c.pt + (now - c.ts) * 1e4, c.dt) : c.pt
  return {
    position: ticksToTime(pos),
    duration: ticksToTime(c.dt),
    pct: ((pos / c.dt) * 100).toFixed(1),
  }
}

export function useStats() {
  const { apiGet } = useApi()
  const run = useStatsLoadRunner()
  const { t } = useI18n()

  function timeAgo(iso) {
    if (!iso) return '—'
    const d = Date.now() - new Date(iso).getTime()
    if (d < 0) return t('common.timeAgo.justNow')
    const s = Math.floor(d / 1000)
    if (s < 60) return t('common.timeAgo.seconds', { n: s })
    const m = Math.floor(s / 60)
    if (m < 60) return t('common.timeAgo.minutes', { n: m })
    const h = Math.floor(m / 60)
    if (h < 24) return t('common.timeAgo.hours', { n: h })
    const dd = Math.floor(h / 24)
    if (dd < 30) return t('common.timeAgo.days', { n: dd })
    return t('common.timeAgo.months', { n: Math.floor(dd / 30) })
  }

  function ticksToDuration(ticks) {
    if (!ticks) return '—'
    const m = Math.floor(ticks / 1e7 / 60)
    if (m < 60) return t('common.duration.min', { n: m })
    const h = Math.floor(m / 60),
      rm = m % 60
    if (h < 24) return t('common.duration.hMin', { h, m: rm })
    const d = Math.floor(h / 24),
      rh = h % 24
    if (d < 30) return t('common.duration.dH', { d, h: rh })
    const mo = Math.floor(d / 30)
    return t('common.duration.moD', { mo, d: d % 30 })
  }

  function loadTotals() {
    return run('loadTotals', { loading: loadingTotals }, async latest => {
      const d = await apiGet('/api/stats/totals')
      if (!d || !latest()) return
      totals.plays = d.total_plays || 0
      totals.duration = d.total_duration_ticks || 0
      totals.users24h = d.active_users_24h || 0
      totals.transcodePct = d.transcode_pct || 0
      totals.storageBytes = d.total_storage_bytes || 0
      totals.totalUsers = d.total_users || 0
      totals.disabledUsers = d.disabled_users || 0
    })
  }

  function loadSparklines() {
    return run('loadSparklines', {}, async latest => {
      const d = await apiGet('/api/stats/chart/daily?days=14&group_by=library')
      if (!d?.days || !latest()) return
      sparklinePlays.value = d.days.map(day => {
        const g = d.data[day] || {}
        return Object.values(g).reduce((s, v) => s + (v.count || 0), 0)
      })
      sparklineDuration.value = d.days.map(day => {
        const g = d.data[day] || {}
        return Object.values(g).reduce((s, v) => s + (v.duration || 0), 0)
      })
    })
  }

  function loadRecords() {
    return run('loadRecords', {}, async latest => {
      const d = await apiGet('/api/stats/records')
      if (latest()) records.value = d
    })
  }

  function loadUserProfile(userId) {
    userProfile.value = null
    const failed = () => {
      userProfile.value = { _error: true }
    }
    return run('loadUserProfile', { notify: false, onFail: failed }, async latest => {
      const d = await apiGet(`/api/stats/users/${encodeURIComponent(userId)}/profile`)
      if (latest()) userProfile.value = d || { _error: true }
    })
  }

  async function fetchSessions() {
    if (sessionInitialLoad) loadingSessions.value = true
    // A poll tries again five seconds later: its failure is logged, not toasted.
    await run('fetchSessions', { notify: false }, async latest => {
      const d = await apiGet('/api/stats/sessions/detailed')
      if (!d || !latest()) return
      sessions.value = d
      const now = Date.now()
      for (const s of d) {
        const k = s.user_id + '_' + s.media
        sessionPositions[k] = {
          pt: parseTicks(s.position),
          dt: parseTicks(s.duration),
          ts: now,
          playing: s.is_playing,
        }
      }
    })
    if (sessionInitialLoad) {
      loadingSessions.value = false
      sessionInitialLoad = false
    }
  }

  function loadPlayback(days = 365) {
    playbackFailed.value = false
    // No cards of another period beside the error: the cards offer a retry instead.
    const failed = () => {
      playback.value = null
      playbackFailed.value = true
    }
    return run('loadPlayback', { loading: loadingPlayback, onFail: failed }, async latest => {
      const d = await apiGet(`/api/stats/playback?days=${days}`)
      if (latest()) playback.value = d
    })
  }

  function loadLibraries() {
    return run('loadLibraries', { loading: loadingLibraries }, async latest => {
      const d = await apiGet('/api/stats/libraries')
      if (d && latest()) libraries.value = d
    })
  }

  function loadUsers({
    page = 1,
    per_page = 30,
    sort_by = 'last_seen',
    sort_order = 'desc',
    search = '',
    show_hidden = false,
    historical_only = false,
  } = {}) {
    return run('loadUsers', { loading: loadingUsers }, async latest => {
      const d = await apiGet(
        `/api/stats/users?page=${page}&per_page=${per_page}&sort_by=${sort_by}&sort_order=${sort_order}&search=${encodeURIComponent(search)}&show_hidden=${show_hidden}&historical_only=${historical_only}`,
      )
      if (d && latest()) users.value = d
    })
  }

  function loadActivity({
    cursor = '',
    limit = 25,
    page = 0,
    perPage = 0,
    search = '',
    excludeUsers = '',
    sortBy = '',
    sortOrder = '',
  } = {}) {
    return run('loadActivity', { loading: loadingActivity }, async latest => {
      const params = new URLSearchParams()
      // page > 0 = flat sorted view (offset paging); otherwise grouped (cursor).
      if (page > 0) {
        params.set('page', page)
        params.set('per_page', perPage || limit)
      } else {
        params.set('limit', limit)
        if (cursor) params.set('cursor', cursor)
      }
      if (search) params.set('search', search)
      if (excludeUsers) params.set('exclude_users', excludeUsers)
      if (sortBy) params.set('sort_by', sortBy)
      if (sortOrder) params.set('sort_order', sortOrder)
      const d = await apiGet(`/api/stats/activity?${params}`)
      if (d && latest()) activity.value = d
    })
  }

  function loadActivityUsers() {
    return run('loadActivityUsers', {}, async latest => {
      const d = await apiGet('/api/stats/activity/users')
      if (Array.isArray(d) && latest()) activityUsers.value = d
    })
  }

  function loadMinimap24h() {
    return run('loadMinimap24h', {}, async latest => {
      const d = await apiGet('/api/stats/activity/minimap')
      if (Array.isArray(d) && latest()) minimap24h.value = d
    })
  }

  function loadDailyChart(days = 30, groupBy = 'library') {
    return run('loadDailyChart', { loading: loadingChart }, async latest => {
      const d = await apiGet(`/api/stats/chart/daily?days=${days}&group_by=${groupBy}`)
      if (latest()) dailyChart.value = d
    })
  }

  function loadHeatmap(days = 90) {
    return run('loadHeatmap', { loading: loadingHeatmap }, async latest => {
      const d = await apiGet(`/api/stats/heatmap?days=${Math.min(days, 365)}`)
      if (latest()) heatmap.value = d
    })
  }

  async function resolveSeriesImageId(seriesName) {
    if (!seriesName) return ''
    if (seriesImageCache[seriesName] !== undefined) return seriesImageCache[seriesName]
    try {
      const d = await apiGet(`/api/stats/series/image/${encodeURIComponent(seriesName)}`)
      seriesImageCache[seriesName] = d?.series_id || ''
    } catch (e) {
      // A missing poster is cosmetic: logged, no toast.
      console.error('[useStats.resolveSeriesImageId]', e)
      seriesImageCache[seriesName] = ''
    }
    return seriesImageCache[seriesName]
  }

  function startSessionPolling() {
    stopSessionPolling()
    fetchSessions()
    pollTimer = setInterval(fetchSessions, 5000)
    tickTimer = setInterval(() => {
      if (sessions.value.some(s => s.is_playing)) sessions.value = [...sessions.value]
    }, 1000)
  }
  function stopSessionPolling() {
    if (pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }
    if (tickTimer) {
      clearInterval(tickTimer)
      tickTimer = null
    }
  }

  return {
    totals,
    sessions,
    playback,
    libraries,
    users,
    activity,
    activityUsers,
    minimap24h,
    dailyChart,
    heatmap,
    sparklinePlays,
    sparklineDuration,
    records,
    userProfile,
    loadingTotals,
    loadingSessions,
    loadingPlayback,
    loadingLibraries,
    loadingUsers,
    loadingActivity,
    loadingChart,
    loadingHeatmap,
    playbackFailed,
    loadTotals,
    fetchSessions,
    loadPlayback,
    loadLibraries,
    loadUsers,
    loadActivity,
    loadActivityUsers,
    loadMinimap24h,
    loadDailyChart,
    loadHeatmap,
    loadSparklines,
    loadRecords,
    loadUserProfile,
    startSessionPolling,
    stopSessionPolling,
    getSessionProgress,
    sessionPositions,
    resolveSeriesImageId,
    ticksToTime,
    ticksToDuration,
    ticksToHours,
    fmtSize,
    timeAgo,
    langLabel,
    langShort,
  }
}
