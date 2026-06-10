import { ref, reactive } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApi } from './useApi'

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

const sessionPositions = reactive({})
let tickTimer = null
let pollTimer = null
let sessionInitialLoad = true
const seriesImageCache = {}

function ticksToTime(t) {
  const s = Math.floor(t / 1e7),
    h = Math.floor(s / 3600),
    m = Math.floor((s % 3600) / 60),
    sec = s % 60
  return `${h}:${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`
}
function ticksToHours(t) {
  if (!t) return '—'
  const h = Math.floor(t / 1e7 / 3600),
    m = Math.floor(((t / 1e7) % 3600) / 60)
  return h > 0 ? `${h.toLocaleString(undefined)}h ${m}min` : `${m}min`
}
function fmtSize(b) {
  if (!b) return '—'
  if (b >= 1099511627776) return `${(b / 1099511627776).toFixed(2)} TB`
  if (b >= 1073741824) return `${(b / 1073741824).toFixed(2)} GB`
  return `${(b / 1048576).toFixed(1)} MB`
}
function langLabel(l) {
  const m = {
    fr: 'French',
    en: 'English',
    de: 'German',
    es: 'Spanish',
    it: 'Italian',
    ja: 'Japanese',
    ko: 'Korean',
    pt: 'Portuguese',
    ru: 'Russian',
    zh: 'Chinese',
    ar: 'Arabic',
    nl: 'Dutch',
    pl: 'Polish',
    sv: 'Swedish',
    da: 'Danish',
    fi: 'Finnish',
    no: 'Norwegian',
    tr: 'Turkish',
    th: 'Thai',
    hi: 'Hindi',
    fre: 'French',
    fra: 'French',
    eng: 'English',
    ger: 'German',
    deu: 'German',
    spa: 'Spanish',
    ita: 'Italian',
    jpn: 'Japanese',
    kor: 'Korean',
    por: 'Portuguese',
    rus: 'Russian',
    chi: 'Chinese',
    zho: 'Chinese',
    ara: 'Arabic',
    dut: 'Dutch',
    nld: 'Dutch',
    pol: 'Polish',
    swe: 'Swedish',
    dan: 'Danish',
    fin: 'Finnish',
    nor: 'Norwegian',
    tur: 'Turkish',
    tha: 'Thai',
    und: 'Unknown',
  }
  return m[(l || '').toLowerCase()] || (l || '').toUpperCase() || ''
}
function langShort(l) {
  const m = {
    fr: 'FR',
    en: 'EN',
    de: 'DE',
    es: 'ES',
    it: 'IT',
    ja: 'JA',
    fre: 'FR',
    eng: 'EN',
    ger: 'DE',
    spa: 'ES',
    jpn: 'JA',
    fra: 'FR',
    deu: 'DE',
    ita: 'IT',
    kor: 'KO',
    por: 'PT',
    rus: 'RU',
  }
  return m[(l || '').toLowerCase()] || ''
}
function parseTicks(str) {
  if (!str) return 0
  const p = str.split(':').map(Number)
  return p.length === 3 ? (p[0] * 3600 + p[1] * 60 + p[2]) * 1e7 : 0
}

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

  async function loadTotals() {
    loadingTotals.value = true
    try {
      const d = await apiGet('/api/stats/totals')
      if (d) {
        totals.plays = d.total_plays || 0
        totals.duration = d.total_duration_ticks || 0
        totals.users24h = d.active_users_24h || 0
        totals.transcodePct = d.transcode_pct || 0
        totals.storageBytes = d.total_storage_bytes || 0
        totals.totalUsers = d.total_users || 0
        totals.disabledUsers = d.disabled_users || 0
      }
    } catch {
      /* silent: stats totals fetch */
    }
    loadingTotals.value = false
  }

  async function loadSparklines() {
    try {
      const d = await apiGet('/api/stats/chart/daily?days=14&group_by=library')
      if (d && d.days) {
        sparklinePlays.value = d.days.map(day => {
          const g = d.data[day] || {}
          return Object.values(g).reduce((s, v) => s + (v.count || 0), 0)
        })
        sparklineDuration.value = d.days.map(day => {
          const g = d.data[day] || {}
          return Object.values(g).reduce((s, v) => s + (v.duration || 0), 0)
        })
      }
    } catch {
      /* silent: sparklines fetch */
    }
  }

  async function loadRecords() {
    try {
      records.value = await apiGet('/api/stats/records')
    } catch {
      /* silent: records fetch */
    }
  }

  async function loadUserProfile(userId) {
    userProfile.value = null
    try {
      const d = await apiGet(`/api/stats/users/${encodeURIComponent(userId)}/profile`)
      userProfile.value = d || { _error: true }
    } catch {
      userProfile.value = { _error: true }
    }
  }

  async function fetchSessions() {
    if (sessionInitialLoad) loadingSessions.value = true
    try {
      const d = await apiGet('/api/stats/sessions/detailed')
      if (d) {
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
      }
    } catch {
      /* silent: sessions poll, retries on next tick */
    }
    if (sessionInitialLoad) {
      loadingSessions.value = false
      sessionInitialLoad = false
    }
  }

  async function loadPlayback(days = 365) {
    loadingPlayback.value = true
    try {
      playback.value = await apiGet(`/api/stats/playback?days=${days}`)
    } catch {
      /* silent: playback fetch */
    }
    loadingPlayback.value = false
  }

  async function loadLibraries() {
    loadingLibraries.value = true
    try {
      const d = await apiGet('/api/stats/libraries')
      if (d) libraries.value = d
    } catch {
      /* silent: libraries fetch */
    }
    loadingLibraries.value = false
  }

  async function loadUsers({
    page = 1,
    per_page = 30,
    sort_by = 'last_seen',
    sort_order = 'desc',
    search = '',
    show_hidden = false,
    historical_only = false,
  } = {}) {
    loadingUsers.value = true
    try {
      const d = await apiGet(
        `/api/stats/users?page=${page}&per_page=${per_page}&sort_by=${sort_by}&sort_order=${sort_order}&search=${encodeURIComponent(search)}&show_hidden=${show_hidden}&historical_only=${historical_only}`,
      )
      if (d) users.value = d
    } catch {
      /* silent: users fetch */
    }
    loadingUsers.value = false
  }

  async function loadActivity({
    cursor = '',
    limit = 25,
    page = 0,
    perPage = 0,
    search = '',
    excludeUsers = '',
    sortBy = '',
    sortOrder = '',
    append = false,
  } = {}) {
    loadingActivity.value = true
    try {
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
      if (d) {
        if (append && d.items)
          activity.value = { ...d, items: [...activity.value.items, ...d.items] }
        else activity.value = d
      }
    } catch {
      /* silent: activity fetch */
    }
    loadingActivity.value = false
  }

  async function loadActivityUsers() {
    try {
      const d = await apiGet('/api/stats/activity/users')
      if (Array.isArray(d)) activityUsers.value = d
    } catch {
      /* silent: activity users fetch */
    }
  }

  async function loadMinimap24h() {
    try {
      const d = await apiGet('/api/stats/activity/minimap')
      if (Array.isArray(d)) minimap24h.value = d
    } catch {
      /* silent: minimap fetch */
    }
  }

  async function loadDailyChart(days = 30, groupBy = 'library') {
    loadingChart.value = true
    try {
      dailyChart.value = await apiGet(`/api/stats/chart/daily?days=${days}&group_by=${groupBy}`)
    } catch {
      /* silent: daily chart fetch */
    }
    loadingChart.value = false
  }

  async function loadHeatmap(days = 90) {
    loadingHeatmap.value = true
    try {
      heatmap.value = await apiGet(`/api/stats/heatmap?days=${Math.min(days, 365)}`)
    } catch {
      /* silent: heatmap fetch */
    }
    loadingHeatmap.value = false
  }

  async function resolveSeriesImageId(seriesName) {
    if (!seriesName) return ''
    if (seriesImageCache[seriesName] !== undefined) return seriesImageCache[seriesName]
    try {
      const d = await apiGet(`/api/stats/series/image/${encodeURIComponent(seriesName)}`)
      seriesImageCache[seriesName] = d?.series_id || ''
    } catch {
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
