import { reactive, onMounted, onUnmounted, watch } from 'vue'
import { useAuth } from './useAuth'
import { useApi } from './useApi'
import { useRouter } from 'vue-router'

/**
 * Live counters shared across the sidebar.
 * Reactive singleton — a single poll even if several components use it.
 * Raw data (sessions, alerts) is also exposed to avoid the dashboard
 * making the same calls again.
 */
const counters = reactive({
  duplicates: 0,
  watchlistMissing: 0,
  activeSessions: 0,
})

// Raw shared data (reusable by other components)
const sharedData = reactive({
  sessions: [],
})

// Immediate retrieval from cache for instant display
try {
  const cached = sessionStorage.getItem('mk_sidebar_counters')
  if (cached) Object.assign(counters, JSON.parse(cached))
} catch {
  /* silent: corrupted sessionStorage cache → keep defaults */
}

let refCount = 0
let timer = null

async function fetchCounters(api) {
  // Do not poll when not authenticated
  const { isAuthenticated } = useAuth()
  if (!isAuthenticated.value) return

  try {
    const [duplicates, watchlist, sessions, ignored] = await Promise.all([
      api.apiGet('/api/duplicates').catch(() => null),
      api.apiGet('/api/watchlist/scan/status').catch(() => null),
      api.apiGet('/api/emby/sessions').catch(() => null),
      api.apiGet('/api/duplicates/ignored').catch(() => null),
    ])

    if (Array.isArray(duplicates)) {
      const ignoredKeys = new Set((Array.isArray(ignored) ? ignored : []).map(i => i.key))
      counters.duplicates = duplicates.filter(
        item => !ignoredKeys.has(`${item.id}_${item.sources.length}`),
      ).length
    }
    if (watchlist) {
      counters.watchlistMissing = watchlist?.total_missing || 0
    }
    if (Array.isArray(sessions)) {
      sharedData.sessions = sessions
      counters.activeSessions = sessions.filter(x => x.is_playing || x.is_paused).length
    }

    try {
      sessionStorage.setItem('mk_sidebar_counters', JSON.stringify(counters))
    } catch {
      /* silent: sessionStorage quota/privacy mode */
    }
  } catch {
    /* silent: counter poll, retries on next interval */
  }
}

export function useSidebarCounters() {
  const api = useApi()

  function refresh() {
    return fetchCounters(api)
  }

  onMounted(() => {
    refCount++
    if (refCount === 1) {
      refresh()
      timer = setInterval(refresh, 45000)
    }
  })

  onUnmounted(() => {
    refCount--
    if (refCount <= 0) {
      refCount = 0
      if (timer) {
        clearInterval(timer)
        timer = null
      }
    }
  })

  // Refresh counters on every route change
  try {
    const router = useRouter()
    watch(
      () => router.currentRoute.value.path,
      () => {
        refresh()
      },
    )
  } catch {
    /* silent: router not available in test/SSR context */
  }

  return { counters, sharedData, fetchCounters: refresh }
}
