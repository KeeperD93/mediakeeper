/**
 * Activity leaderboard — fetch one period with a small SWR cache.
 *
 * The dedicated /portal/leaderboard page fetches the top-100 ranking
 * of a period plus the viewer-aware payload that powers the
 * hero billboard, live stats bar and "my rank" card:
 *
 *   { items, viewer_rank, viewer_entry, stats }
 *
 * Each entry mirrors the schema returned by /api/portal/profiles/me
 * mini-leaderboard (rank, user_id, display_name, avatar_url, level,
 * tier, title_key, period_xp, selected_title, title_tier,
 * is_current_user, movement) so the gc-lb-* CSS classes from
 * leaderboard-card.css apply without translation.
 *
 * A 30 s in-flight + memo window per period and size keeps the network
 * quiet when the user toggles tabs or routes (router guard hits
 * portalLayout endpoints on every nav).
 */
import { ref } from 'vue'
import { useApi } from '@/composables/useApi'
import { LEADERBOARD_PAGE_LIMIT, LEADERBOARD_PERIOD } from '@/constants/leaderboard'

const MEMO_TTL_MS = 30_000

const memo = new Map()
const inflight = new Map()

function emptyPayload() {
  return {
    items: [],
    viewer_rank: null,
    viewer_entry: null,
    stats: null,
  }
}

function loadOnce(apiGet, key, limit, period) {
  if (inflight.has(key)) return inflight.get(key)
  const pending = apiGet(
    `/api/portal/achievements/leaderboard/activity?period=${period}&limit=${limit}`,
  )
    .then(res => {
      const payload = {
        items: res?.items || [],
        viewer_rank: res?.viewer_rank ?? null,
        viewer_entry: res?.viewer_entry ?? null,
        stats: res?.stats ?? null,
      }
      memo.set(key, { payload, at: Date.now() })
      return payload
    })
    .finally(() => inflight.delete(key))
  inflight.set(key, pending)
  return pending
}

export function useActivityLeaderboard() {
  const { apiGet } = useApi()
  const entries = ref([])
  const viewerRank = ref(null)
  const viewerEntry = ref(null)
  const stats = ref(null)
  const loading = ref(false)
  const error = ref(null)
  let lastRequest = 0

  function applyPayload(payload) {
    entries.value = payload?.items || []
    viewerRank.value = payload?.viewer_rank ?? null
    viewerEntry.value = payload?.viewer_entry ?? null
    stats.value = payload?.stats ?? null
  }

  async function fetchTop(
    limit = LEADERBOARD_PAGE_LIMIT,
    { period = LEADERBOARD_PERIOD.MONTH } = {},
  ) {
    const request = ++lastRequest
    const key = `${period}:${limit}`
    error.value = null
    const hit = memo.get(key)
    if (hit && Date.now() - hit.at < MEMO_TTL_MS) {
      applyPayload(hit.payload)
      loading.value = false
      return hit.payload
    }
    loading.value = true
    let payload
    let failure = null
    try {
      payload = await loadOnce(apiGet, key, limit, period)
    } catch (err) {
      failure = err?.data?.detail || 'fetch_failed'
      payload = emptyPayload()
    }
    // The last tab clicked wins: a slower answer for an earlier one only fills the memo.
    if (request === lastRequest) {
      applyPayload(payload)
      error.value = failure
      loading.value = false
    }
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
