import { ref } from 'vue'

const FAIL_THRESHOLD = 3
const POLL_INTERVAL_MS = 5000

/**
 * Polls /api/health to drive the reconnect overlay.
 *
 * Detects backend rebuilds via the `boot_id` field: when the identifier
 * changes between two successful checks, the JWT may be stale (Fernet
 * key rotation, session purge), so we force a logout + redirect to /login.
 * Same boot_id after a downtime is the legacy reload-in-place behaviour.
 */
export function useBackendHealth({
  fetchApiResponse,
  router,
  logout,
  showToast,
  t,
  reload = () => window.location.reload(),
  setInterval: setIntervalFn = (cb, ms) => setInterval(cb, ms),
  clearInterval: clearIntervalFn = id => clearInterval(id),
}) {
  const backendDown = ref(false)
  let pollHandle = null
  let failCount = 0
  let knownBootId = null

  async function handleRebuilt() {
    backendDown.value = false
    knownBootId = null
    try {
      await logout()
    } catch {
      /* ignore — UI redirect is the priority */
    }
    if (showToast && t) {
      showToast(t('app.rebuilt_logout'), 'info')
    }
    try {
      await router.push('/login')
    } catch {
      /* ignore navigation errors (already on /login etc.) */
    }
  }

  async function tick() {
    if (router.currentRoute.value?.name === 'login') {
      failCount = 0
      backendDown.value = false
      return
    }

    let res
    try {
      res = await fetchApiResponse('/api/health', {
        retryOn401: false,
        redirectOn401: false,
      })
    } catch {
      failCount++
      if (failCount >= FAIL_THRESHOLD) backendDown.value = true
      return
    }

    if (!res?.ok) {
      failCount++
      if (failCount >= FAIL_THRESHOLD) backendDown.value = true
      return
    }

    let receivedBootId = null
    try {
      const data = await res.json()
      receivedBootId = typeof data?.boot_id === 'string' ? data.boot_id : null
    } catch {
      /* response body absent or non-JSON: treat as legacy backend */
    }

    if (knownBootId === null) {
      knownBootId = receivedBootId
      if (backendDown.value) {
        backendDown.value = false
        reload()
      }
    } else if (receivedBootId && receivedBootId !== knownBootId) {
      await handleRebuilt()
    } else if (backendDown.value) {
      backendDown.value = false
      reload()
    }

    failCount = 0
  }

  function start() {
    if (pollHandle) return
    pollHandle = setIntervalFn(tick, POLL_INTERVAL_MS)
  }

  function stop() {
    if (pollHandle) {
      clearIntervalFn(pollHandle)
      pollHandle = null
    }
  }

  return {
    backendDown,
    start,
    stop,
    tick,
  }
}
