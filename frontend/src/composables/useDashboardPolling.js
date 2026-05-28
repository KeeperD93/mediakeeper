/**
 * Two-tier polling lifecycle for the desktop dashboard.
 *
 * Split out of DashboardView.vue so the page stays focused on layout
 * and template orchestration. The composable owns:
 *   - the primary loaders fired on mount (system stats, services,
 *     sessions, seen alerts)
 *   - the secondary loaders deferred to an idle callback so they
 *     don't compete with the initial paint
 *   - the setInterval timers refreshing both tiers
 *   - the teardown on unmount so cached pages don't leak handlers
 *
 * Consumers pass the loader functions from ``useDashboardData`` and
 * call ``start()`` once their layout state is ready (typically right
 * after ``await loadLayout()`` in the page's onMounted).
 */
import { onUnmounted } from 'vue'

const PRIMARY_INTERVAL_SYSTEM_MS = 10_000
const PRIMARY_INTERVAL_SESSIONS_MS = 15_000
const PRIMARY_INTERVAL_SERVICES_MS = 60_000

const SECONDARY_INTERVAL_LOGS_MS = 15_000
const SECONDARY_INTERVAL_ALERTS_MS = 30_000
const SECONDARY_INTERVAL_MEDIA_STATS_MS = 60_000
const SECONDARY_INTERVAL_WATCHLIST_MS = 30_000

const IDLE_CALLBACK_TIMEOUT_MS = 1500

function queueDeferredLoad(task) {
  if (typeof window !== 'undefined' && typeof window.requestIdleCallback === 'function') {
    window.requestIdleCallback(
      () => {
        void task()
      },
      { timeout: IDLE_CALLBACK_TIMEOUT_MS },
    )
    return
  }
  window.setTimeout(() => {
    void task()
  }, 0)
}

export function useDashboardPolling({
  loadSeenAlerts,
  loadSystemStats,
  loadServices,
  loadSessions,
  loadLogs,
  loadAlerts,
  loadDuplicates,
  loadWatchlist,
  loadMediaStats,
  loadLeaderboard,
}) {
  const timers = []
  let secondaryLoadStarted = false

  function startPrimaryPolling() {
    timers.push(
      setInterval(loadSystemStats, PRIMARY_INTERVAL_SYSTEM_MS),
      setInterval(loadSessions, PRIMARY_INTERVAL_SESSIONS_MS),
      setInterval(loadServices, PRIMARY_INTERVAL_SERVICES_MS),
    )
  }

  function startSecondaryPolling() {
    timers.push(
      setInterval(loadLogs, SECONDARY_INTERVAL_LOGS_MS),
      setInterval(loadAlerts, SECONDARY_INTERVAL_ALERTS_MS),
      setInterval(loadMediaStats, SECONDARY_INTERVAL_MEDIA_STATS_MS),
      setInterval(loadWatchlist, SECONDARY_INTERVAL_WATCHLIST_MS),
    )
  }

  function scheduleSecondaryLoad() {
    if (secondaryLoadStarted) return
    secondaryLoadStarted = true
    queueDeferredLoad(async () => {
      await Promise.all([
        loadLogs(),
        loadAlerts(),
        loadDuplicates(),
        loadWatchlist(),
        loadMediaStats(),
        loadLeaderboard(),
      ])
      startSecondaryPolling()
    })
  }

  async function start() {
    await Promise.all([loadSeenAlerts(), loadSystemStats(), loadServices(), loadSessions()])
    startPrimaryPolling()
    scheduleSecondaryLoad()
  }

  onUnmounted(() => {
    timers.forEach(clearInterval)
  })

  return { start }
}
