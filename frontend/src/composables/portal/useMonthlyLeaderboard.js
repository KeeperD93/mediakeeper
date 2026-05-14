/**
 * Monthly leaderboard — fetch with a small SWR cache.
 *
 * The dedicated /portal/leaderboard page fetches the top-100 ranking
 * for the current month plus the viewer-aware payload that powers the
 * hero billboard, live stats bar and "my rank" card:
 *
 *   { items, viewer_rank, viewer_entry, stats }
 *
 * Each entry mirrors the schema returned by /api/portal/profiles/me
 * mini-leaderboard (rank, user_id, display_name, avatar_url, level,
 * tier, title_key, month_xp, selected_title, title_tier,
 * is_current_user, movement) so the gc-lb-* CSS classes from
 * leaderboard-card.css apply without translation.
 *
 * A 30 s in-flight + memo window keeps the network quiet when the user
 * toggles routes (router guard hits portalLayout endpoints on every nav).
 */
import { ref } from 'vue'
import { useApi } from '@/composables/useApi'

const MEMO_TTL_MS = 30_000

let cached = null
let cachedAt = 0
let inflight = null

function emptyPayload() {
  return {
    items: [],
    viewer_rank: null,
    viewer_entry: null,
    stats: null,
  }
}

export function useMonthlyLeaderboard() {
  const { apiGet } = useApi()
  const entries = ref([])
  const viewerRank = ref(null)
  const viewerEntry = ref(null)
  const stats = ref(null)
  const loading = ref(false)
  const error = ref(null)

  function applyPayload(payload) {
    entries.value = payload?.items || []
    viewerRank.value = payload?.viewer_rank ?? null
    viewerEntry.value = payload?.viewer_entry ?? null
    stats.value = payload?.stats ?? null
  }

  async function fetchTop(limit = 100, { force = false } = {}) {
    const now = Date.now()
    if (!force && cached && now - cachedAt < MEMO_TTL_MS) {
      applyPayload(cached)
      return cached
    }
    if (inflight) {
      const res = await inflight
      applyPayload(res)
      return res
    }
    loading.value = true
    error.value = null
    inflight = (async () => {
      try {
        const res = await apiGet(
          `/api/portal/achievements/leaderboard/monthly?limit=${limit}`,
        )
        const payload = {
          items: res?.items || [],
          viewer_rank: res?.viewer_rank ?? null,
          viewer_entry: res?.viewer_entry ?? null,
          stats: res?.stats ?? null,
        }
        cached = payload
        cachedAt = Date.now()
        return payload
      } catch (err) {
        error.value = err?.data?.detail || 'fetch_failed'
        return emptyPayload()
      } finally {
        inflight = null
      }
    })()
    const payload = await inflight
    applyPayload(payload)
    loading.value = false
    return payload
  }

  return {
    entries,
    viewerRank,
    viewerEntry,
    stats,
    loading,
    error,
    fetchTop,
  }
}
