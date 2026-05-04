import { ref, computed, readonly } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApi } from './useApi'
import { useToast } from './useToast'
import { TOAST_TYPE } from '@/constants/toast'
import { isMovie } from '@/constants/media'
import { EPISODE_STATUS } from '@/constants/watchlist'
import { TRAILER_SOURCE } from '@/constants/trailers'

// ---- Singleton state ----
const data = ref(null)
const ignored = ref([])
const tracked = ref([])
const loading = ref(false)
const calCache = {}
let calDirty = false

// Timeline & Calendar — singleton, pre-filled in the background
const timelineItems = ref([])
const timelineLoading = ref(true)
const calVersion = ref(0) // notifie le calendrier d'un changement de mois

const { apiGet, apiFetch, apiPost } = useApi()
const { showToast } = useToast()
let _t = k => k // fallback until useI18n is initialized

// ---- Computed ----
const ignoredSet = computed(() => new Set(ignored.value))

const missingCount = computed(() => {
  if (!data.value?.series) return 0
  const ign = ignoredSet.value
  return data.value.series.reduce(
    (sum, s) =>
      sum +
      (s.seasons || []).reduce(
        (a, sn) =>
          a +
          sn.episodes.filter(
            e =>
              e.status === EPISODE_STATUS.MISSING &&
              !ign.has(`${s.tmdb_id}_s${sn.season}_e${e.episode}`),
          ).length,
        0,
      ),
    0,
  )
})

const upcomingCount = computed(() => {
  if (!data.value?.series) return 0
  return data.value.series.reduce((sum, s) => sum + (s.upcoming_count || 0), 0)
})

// ---- Actions ----

async function loadIgnored() {
  try {
    const d = await apiGet('/api/watchlist/ignored')
    if (d?.ignored) ignored.value = d.ignored
  } catch {
    /* ignore */
  }
}

async function loadTracked() {
  try {
    const d = await apiGet('/api/watchlist/tracked')
    if (Array.isArray(d)) tracked.value = d
  } catch {
    /* ignore */
  }
}

async function loadScan() {
  if (loading.value) return
  loading.value = true
  try {
    const d = await apiGet('/api/watchlist/scan')
    if (d) data.value = d
  } catch {
    /* ignore */
  }
  loading.value = false
}

async function refreshScan() {
  loading.value = true
  try {
    const res = await apiFetch('/api/watchlist/scan/refresh', { method: 'POST' })
    if (res) {
      const d = await res.json()
      data.value = d
      showToast(_t('watchlist.scanDone'), TOAST_TYPE.OK)
    }
  } catch {
    showToast(_t('watchlist.scanError'), TOAST_TYPE.ERR)
  }
  loading.value = false
}

async function ignoreEpisode(key) {
  ignored.value.push(key)
  try {
    await apiPost('/api/watchlist/ignored/add', { keys: [key] })
  } catch {
    /* ignore */
  }
  showToast(_t('watchlist.episodeIgnored'), TOAST_TYPE.OK, 2000)
}

async function ignoreMultiple(keys) {
  for (const k of keys) if (!ignored.value.includes(k)) ignored.value.push(k)
  try {
    await apiPost('/api/watchlist/ignored/add', { keys })
  } catch {
    /* ignore */
  }
  showToast(_t('watchlist.ignoredCount', { count: keys.length }), TOAST_TYPE.OK, 2000)
}

async function restoreKeys(keys) {
  try {
    await apiPost('/api/watchlist/ignored/remove', { keys })
    ignored.value = ignored.value.filter(k => !keys.includes(k))
    showToast(_t('watchlist.restored'), TOAST_TYPE.OK, 2000)
  } catch {
    /* ignore */
  }
}

async function toggleTrack(item) {
  const isT = tracked.value.some(
    t => t.tmdb_id === item.tmdb_id && t.media_type === item.media_type,
  )
  try {
    if (isT) {
      await apiPost('/api/watchlist/tracked/remove', {
        tmdb_id: item.tmdb_id,
        media_type: item.media_type,
      })
      tracked.value = tracked.value.filter(
        t => !(t.tmdb_id === item.tmdb_id && t.media_type === item.media_type),
      )
      _removeFromCalCache(item.tmdb_id)
    } else {
      await apiPost('/api/watchlist/tracked/add', {
        tmdb_id: item.tmdb_id,
        media_type: item.media_type,
        name: item.name,
        poster: item.poster || '',
        overview: item.overview || '',
        release_date: item.release_date || '',
        year: item.year || '',
        total_seasons: item.total_seasons || 0,
        total_episodes: item.total_episodes || 0,
      })
      tracked.value.push(item)
      if (isMovie(item) && item.release_date) {
        _addMovieToCalCache(item)
      } else {
        calDirty = true
      }
    }
    // Instant rebuild from the refreshed cache
    _rebuildTimeline()
    calVersion.value++
    showToast(isT ? _t('watchlist.unfollowed') : _t('watchlist.followed'), TOAST_TYPE.OK, 2000)
  } catch {
    showToast(_t('common.networkError'), TOAST_TYPE.ERR)
  }
}

function _removeFromCalCache(tmdbId) {
  for (const ck of Object.keys(calCache)) {
    if (Array.isArray(calCache[ck])) {
      calCache[ck] = calCache[ck].filter(it => it.tmdb_id !== tmdbId)
    }
  }
}

function _addMovieToCalCache(item) {
  if (!item.release_date) return
  const [y, m] = item.release_date.split('-')
  const ck = `${parseInt(y)}-${parseInt(m)}`
  if (!calCache[ck]) return
  calCache[ck].push({
    date: item.release_date,
    series_name: item.name,
    series_id: '',
    tmdb_id: item.tmdb_id,
    season: 0,
    episode: 0,
    episode_name: _t('dashboard.movieRelease'),
    poster: item.poster || '',
    emby_poster: '',
    source: TRAILER_SOURCE.TRACKED,
    overview: (item.overview || '').slice(0, 300),
    total_seasons: 0,
    total_episodes: 0,
    first_air_date: item.release_date,
    is_movie: true,
  })
  calCache[ck].sort((a, b) => a.date.localeCompare(b.date))
}

function _rebuildTimeline() {
  const seen = new Set(),
    out = []
  for (const items of Object.values(calCache)) {
    if (!Array.isArray(items)) continue
    for (const it of items) {
      const k = `${it.series_name}_${it.date}_${it.season}_${it.episode}`
      if (!seen.has(k)) {
        seen.add(k)
        out.push({ ...it, _key: k })
      }
    }
  }
  timelineItems.value = out.sort((a, b) => a.date.localeCompare(b.date))
}

function isTracked(tmdbId, mediaType) {
  return tracked.value.some(t => t.tmdb_id === tmdbId && t.media_type === mediaType)
}

async function getCalendar(year, month) {
  if (calDirty) {
    Object.keys(calCache).forEach(k => delete calCache[k])
    calDirty = false
  }
  const ck = `${year}-${month}`
  if (calCache[ck]) return calCache[ck]
  try {
    const d = await apiGet(`/api/watchlist/calendar?year=${year}&month=${month}`)
    if (d) calCache[ck] = d
    return d || []
  } catch {
    return []
  }
}

async function prefetchCalendar() {
  const n = new Date()

  // Phase 1 : 3 mois urgents (autour d'aujourd'hui)
  const urgent = []
  for (let i = -1; i <= 1; i++) {
    const d = new Date(n.getFullYear(), n.getMonth() + i, 1)
    urgent.push(getCalendar(d.getFullYear(), d.getMonth() + 1))
  }
  await Promise.all(urgent)
  _rebuildTimeline()
  timelineLoading.value = false

  // Phase 2: the remaining 12 months in the background
  const remaining = []
  for (let i = -7; i <= 7; i++) {
    if (i >= -1 && i <= 1) continue
    const d = new Date(n.getFullYear(), n.getMonth() + i, 1)
    remaining.push({ y: d.getFullYear(), m: d.getMonth() + 1 })
  }
  for (let j = 0; j < remaining.length; j += 3) {
    const batch = remaining.slice(j, j + 3).map(r => getCalendar(r.y, r.m))
    await Promise.all(batch)
    _rebuildTimeline()
  }
}

async function searchTMDB(q) {
  try {
    const res = await apiFetch(`/api/watchlist/search?q=${encodeURIComponent(q)}`)
    if (res?.ok) return await res.json()
    return []
  } catch {
    return []
  }
}

export function useWatchlist() {
  const { t } = useI18n()
  _t = t
  return {
    data: readonly(data),
    ignored,
    tracked,
    loading: readonly(loading),
    ignoredSet,
    missingCount,
    upcomingCount,
    loadIgnored,
    loadTracked,
    loadScan,
    refreshScan,
    ignoreEpisode,
    ignoreMultiple,
    restoreKeys,
    toggleTrack,
    isTracked,
    getCalendar,
    calVersion,
    timelineItems: readonly(timelineItems),
    timelineLoading: readonly(timelineLoading),
    prefetchCalendar,
    searchTMDB,
  }
}
