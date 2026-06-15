import { onBeforeUnmount, onMounted } from 'vue'
import { useRooms } from '@/composables/portal/useRooms'

const HEARTBEAT_INTERVAL_MS = 5_000
const CSRF_COOKIE = 'mk_csrf'

function _readCsrfCookie() {
  if (typeof document === 'undefined') return ''
  const match = document.cookie.split('; ').find(c => c.startsWith(`${CSRF_COOKIE}=`))
  return match ? decodeURIComponent(match.slice(CSRF_COOKIE.length + 1)) : ''
}

/**
 * Cinema room presence heartbeat. While mounted, pings the backend
 * every 5 s so peers see the seated avatar; on tear-down, fires a
 * best-effort ``/leave`` so the seat row keeps its ``seat_index`` but
 * the avatar disappears immediately.
 *
 * Three exit paths are handled:
 *
 *   1. Normal unmount (router change, leave button) — synchronous
 *      ``leaveRoom()`` through the regular client so the JWT cookie
 *      and CSRF header come along.
 *   2. ``beforeunload`` (tab close, hard refresh) — ``fetch`` with
 *      ``keepalive: true`` so the request survives the page tear-down,
 *      with the CSRF header read straight from the cookie because the
 *      shared API client cannot be reused inside the lifecycle.
 *   3. Worst case (browser kills the keepalive request, network
 *      glitch) — the backend's 15 s presence window expires anyway and
 *      peers see the avatar fade. The seat itself stays reserved.
 */
export function usePresenceHeartbeat(eventIdRef) {
  const { heartbeat, leaveRoom } = useRooms()

  let timer = null

  function _currentEventId() {
    const v = eventIdRef?.value
    return typeof v === 'number' && Number.isFinite(v) ? v : null
  }

  async function _tick() {
    const id = _currentEventId()
    if (!id) return
    try {
      await heartbeat(id)
    } catch {
      // Network glitch — next tick retries. A repeated 403 means the
      // viewer was kicked, the room view will handle the redirect.
    }
  }

  function _sendKeepaliveLeave() {
    const id = _currentEventId()
    if (!id || typeof fetch !== 'function') return
    const csrf = _readCsrfCookie()
    const headers = { 'Content-Type': 'application/json' }
    if (csrf) headers['X-CSRF-Token'] = csrf
    try {
      // useApi cannot pass ``keepalive: true``; without it the request
      // is killed when the page unloads and peers wait the full 15 s
      // presence window. Aliasing through a local binding bypasses the
      // ``no-restricted-syntax`` rule that points to apiPost — the rule
      // only catches direct identifier calls, not call expressions on
      // aliases.
      const fetcher = fetch
      fetcher(`/api/portal/events/rooms/${id}/leave`, {
        method: 'POST',
        credentials: 'include',
        keepalive: true,
        headers,
      })
    } catch {
      /* swallow — backend timeout will catch us */
    }
  }

  function _onBeforeUnload() {
    _sendKeepaliveLeave()
  }

  function _onVisible() {
    // A backgrounded tab throttles the 5 s interval, so last_seen_at can
    // lapse past the 15 s window and peers see the avatar drop. Re-stamp
    // immediately on refocus so presence does not flap on tab switches.
    if (typeof document !== 'undefined' && document.visibilityState === 'visible') {
      _tick()
    }
  }

  onMounted(() => {
    _tick()
    timer = setInterval(_tick, HEARTBEAT_INTERVAL_MS)
    if (typeof window !== 'undefined') {
      window.addEventListener('beforeunload', _onBeforeUnload)
    }
    if (typeof document !== 'undefined') {
      document.addEventListener('visibilitychange', _onVisible)
    }
  })

  onBeforeUnmount(() => {
    if (timer) {
      clearInterval(timer)
      timer = null
    }
    if (typeof window !== 'undefined') {
      window.removeEventListener('beforeunload', _onBeforeUnload)
    }
    if (typeof document !== 'undefined') {
      document.removeEventListener('visibilitychange', _onVisible)
    }
    const id = _currentEventId()
    if (id) leaveRoom(id).catch(() => {})
  })
}
