import { computed, ref } from 'vue'
import { useApi } from '@/composables/useApi'

const POLL_INTERVAL_MS = 3000

/**
 * Cinema room — playback progress poller. Polls the backend snapshot
 * every 3 s while ``enabled`` is true so the launch panel can refresh
 * the per-participant timer without forcing a page reload. The
 * composable exposes:
 *
 *   - ``progress``  : last payload from the server (null until the
 *     first fetch resolves).
 *   - ``loading``   : true during the active fetch.
 *   - ``error``     : last error message, cleared on every successful tick.
 *   - ``enabled``   : whether the poller is currently armed.
 *   - ``ready``     : convenience computed mirroring ``progress.ready``.
 *   - ``start()`` / ``stop()`` / ``bump()``.
 *
 * Single-film events: the payload still arrives with ``is_marathon=
 * false`` but now carries ``participants``, ``current_tmdb`` and
 * ``total_steps=1`` so the cinema room can render the same playback
 * panel as a marathon. We no longer auto-stop the poller on that
 * flag — the room polls until the view is torn down.
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

  // Public alias for ``fetchOnce`` so callers can force a refresh
  // outside the regular 3 s tick — e.g. just after a viewer presses
  // ``Lancer le film`` we want the panel to surface their session
  // sooner than the next scheduled tick.
  function bump() {
    if (!enabled.value) start()
    else fetchOnce()
  }

  const ready = computed(() => Boolean(progress.value?.ready))

  return { progress, loading, error, enabled, ready, start, stop, bump }
}
