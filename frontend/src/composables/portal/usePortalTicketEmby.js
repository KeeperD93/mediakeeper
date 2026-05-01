import { ref } from 'vue'
import { useApi } from '@/composables/useApi'

const SEARCH_DEBOUNCE_MS = 250
const MIN_QUERY_LENGTH = 2

/**
 * Library autocomplete + season tree for the ticket creation flow.
 * Only the picker should call this — other ticket helpers stay in
 * usePortalTickets.js.
 */
export function usePortalTicketEmby() {
  const { apiGet } = useApi()

  const results = ref([])
  const searching = ref(false)
  const lastQuery = ref('')
  let _debounceTimer = null
  let _activeRequest = 0

  function searchDebounced(query) {
    clearTimeout(_debounceTimer)
    const q = (query || '').trim()
    lastQuery.value = q

    if (q.length < MIN_QUERY_LENGTH) {
      results.value = []
      searching.value = false
      return
    }

    searching.value = true
    _debounceTimer = setTimeout(() => _runSearch(q), SEARCH_DEBOUNCE_MS)
  }

  async function _runSearch(q) {
    const reqId = ++_activeRequest
    try {
      const url = `/api/portal/tickets/emby/search?q=${encodeURIComponent(q)}&limit=10`
      const res = await apiGet(url)
      // Drop stale responses — the user kept typing and the latest
      // request is now older than the next one we already fired.
      if (reqId !== _activeRequest) return
      results.value = res?.items || []
    } catch {
      if (reqId === _activeRequest) results.value = []
    } finally {
      if (reqId === _activeRequest) searching.value = false
    }
  }

  function clearResults() {
    clearTimeout(_debounceTimer)
    _activeRequest++
    results.value = []
    searching.value = false
    lastQuery.value = ''
  }

  async function fetchSeriesSeasons(seriesId) {
    if (!seriesId) return []
    try {
      const res = await apiGet(`/api/portal/tickets/emby/series/${encodeURIComponent(seriesId)}/seasons`)
      return res?.seasons || []
    } catch {
      return []
    }
  }

  return {
    results,
    searching,
    lastQuery,
    searchDebounced,
    clearResults,
    fetchSeriesSeasons,
    MIN_QUERY_LENGTH,
  }
}
