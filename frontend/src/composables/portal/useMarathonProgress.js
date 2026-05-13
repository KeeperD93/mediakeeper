import { computed, ref } from 'vue'
import { useApi } from '@/composables/useApi'

const POLL_INTERVAL_MS = 5000

/**
 * Cinema room — marathon progress poller. Polls the backend snapshot
 * every 5 s while ``enabled`` is true. The composable exposes:
 *
 *   - ``progress``  : last payload from the server (null until the
 *     first fetch resolves).
 *   - ``loading``   : true during the active fetch.
 *   - ``error``     : last error message, cleared on every successful tick.
 *   - ``enabled``   : whether the poller is currently armed.
 *   - ``ready``     : convenience computed mirroring ``progress.ready``.
 *   - ``start()`` / ``stop()``.
 *
 * Auto-stop guard: when the server says ``is_marathon=false`` the
 * poller flips ``enabled=false`` and returns — the cinema room only
 * needs marathon updates for multi-film events.
 */
export function useMarathonProgress(eventId) {
  const { apiGet } = useApi()

  const progress = ref(null)
  const loading = ref(false)
  const error = ref(null)
  const enabled = ref(false)

  let timer = null

  async function fetchOnce() {
    if (!eventId) return
    loading.value = true
    try {
      const payload = await apiGet(
        `/api/portal/events/rooms/${eventId}/marathon-progress`,
      )
      progress.value = payload
      error.value = null
      if (payload && payload.is_marathon === false) {
        stop()
      }
    } catch (err) {
      error.value = err instanceof Error ? err.message : String(err)
    } finally {
      loading.value = false
    }
  }

  function start() {
    if (enabled.value) return
    enabled.value = true
    fetchOnce()
    timer = setInterval(fetchOnce, POLL_INTERVAL_MS)
  }

  function stop() {
    enabled.value = false
    if (timer) {
      clearInterval(timer)
      timer = null
    }
  }

  const ready = computed(() => Boolean(progress.value?.ready))

  return { progress, loading, error, enabled, ready, start, stop }
}
