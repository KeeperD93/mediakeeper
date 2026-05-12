/**
 * Portal maintenance-mode state — memoised fetch.
 *
 * The router guard hits this on every navigation, so we cache the
 * answer for 30 s to avoid hammering the backend. ``refresh()`` busts
 * the cache (used after the admin toggles the flag in
 * /portal/settings → AdminSettings).
 */
import { fetchApiResponse } from '@/composables/useApi'

const MEMO_TTL_MS = 30_000

let cached = null
let cachedAt = 0
let inflight = null

export function useMaintenance() {
  async function fetchMaintenanceState({ force = false } = {}) {
    const now = Date.now()
    if (!force && cached && now - cachedAt < MEMO_TTL_MS) {
      return cached
    }
    if (inflight) return inflight
    inflight = (async () => {
      try {
        const res = await fetchApiResponse('/api/portal/maintenance', {
          retryOn401: false,
          redirectOn401: false,
        })
        if (res?.ok) {
          const data = await res.json()
          cached = data
          cachedAt = Date.now()
          return data
        }
      } catch {
        // Network failure: never block the SPA. Treat as "off".
      } finally {
        inflight = null
      }
      cached = cached || { enabled: false, text: '' }
      cachedAt = Date.now()
      return cached
    })()
    return inflight
  }

  function refresh() {
    cached = null
    cachedAt = 0
  }

  return { fetchMaintenanceState, refresh }
}
