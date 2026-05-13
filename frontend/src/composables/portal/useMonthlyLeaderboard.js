/**
 * Monthly leaderboard — fetch with a small SWR cache.
 *
 * The dedicated /portal/leaderboard page fetches the top-100 ranking
 * for the current month. The data shape mirrors the embedded
 * mini-leaderboard returned by /api/portal/profiles/me (same entry
 * keys: rank, user_id, display_name, avatar_url, level, tier,
 * title_key, month_xp, selected_title, title_tier, is_current_user,
 * movement) so the gc-lb-* CSS classes from leaderboard-card.css
 * apply without translation.
 *
 * A 30 s in-flight + memo window keeps the network quiet when the
 * user toggles routes (router guard hits portalLayout endpoints on
 * every nav).
 */
import { ref } from 'vue'
import { useApi } from '@/composables/useApi'

const MEMO_TTL_MS = 30_000

let cached = null
let cachedAt = 0
let inflight = null

export function useMonthlyLeaderboard() {
  const { apiGet } = useApi()
  const entries = ref([])
  const loading = ref(false)
  const error = ref(null)

  async function fetchTop(limit = 100, { force = false } = {}) {
    const now = Date.now()
    if (!force && cached && now - cachedAt < MEMO_TTL_MS) {
      entries.value = cached
      return cached
    }
    if (inflight) {
      const res = await inflight
      entries.value = res
      return res
    }
    loading.value = true
    error.value = null
    inflight = (async () => {
      try {
        const res = await apiGet(`/api/portal/achievements/leaderboard/monthly?limit=${limit}`)
        const items = res?.items || []
        cached = items
        cachedAt = Date.now()
        return items
      } catch (err) {
        error.value = err?.data?.detail || 'fetch_failed'
        return []
      } finally {
        inflight = null
      }
    })()
    const items = await inflight
    entries.value = items
    loading.value = false
    return items
  }

  return { entries, loading, error, fetchTop }
}
