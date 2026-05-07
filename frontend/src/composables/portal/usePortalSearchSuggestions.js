import { ref } from 'vue'
import { useApi } from '@/composables/useApi'

const MIN_LENGTH = 2
const MAX_RESULTS = 5
const DEFAULT_DEBOUNCE_MS = 250

export function usePortalSearchSuggestions(options = {}) {
  const { apiGet } = useApi()
  const debounceMs =
    typeof options.debounceMs === 'number' ? options.debounceMs : DEFAULT_DEBOUNCE_MS

  const suggestions = ref([])
  const loading = ref(false)
  // pending stays true between the moment a new query is scheduled and the
  // moment a fetch for that exact query has settled. The component uses it
  // to gate the "no suggestions" empty state — without it the empty message
  // flashes during the debounce window and during in-flight fetches.
  const pending = ref(false)
  const lastQuery = ref('')

  let token = 0
  let pendingTimer = null

  function clearTimer() {
    if (pendingTimer != null) {
      clearTimeout(pendingTimer)
      pendingTimer = null
    }
  }

  function reset() {
    clearTimer()
    token += 1
    suggestions.value = []
    loading.value = false
    pending.value = false
    lastQuery.value = ''
  }

  async function runFetch(query) {
    const localToken = ++token
    loading.value = true
    try {
      const url = `/api/portal/catalog/search?q=${encodeURIComponent(query)}&page=1`
      const res = await apiGet(url)
      if (localToken !== token) return
      const items = Array.isArray(res?.items) ? res.items : []
      const trimmed = items.slice(0, MAX_RESULTS).map(item => ({
        id: item.tmdb_id ?? item.id ?? null,
        media_type: item.media_type || 'movie',
        title: typeof item.title === 'string' ? item.title : '',
        year: item.year ?? null,
      }))
      suggestions.value = trimmed.filter(item => item.title)
      lastQuery.value = query
    } catch {
      if (localToken === token) {
        suggestions.value = []
        lastQuery.value = query
      }
    } finally {
      if (localToken === token) {
        loading.value = false
        pending.value = false
      }
    }
  }

  function search(rawQuery) {
    const query = (rawQuery || '').trim()
    clearTimer()
    if (query.length < MIN_LENGTH) {
      token += 1
      suggestions.value = []
      loading.value = false
      pending.value = false
      lastQuery.value = ''
      return
    }
    // Skip a redundant fetch when nothing has changed since the last result.
    if (query === lastQuery.value && !pending.value) return
    pending.value = true
    pendingTimer = setTimeout(() => {
      pendingTimer = null
      runFetch(query)
    }, debounceMs)
  }

  return {
    suggestions,
    loading,
    pending,
    lastQuery,
    search,
    reset,
    minLength: MIN_LENGTH,
    maxResults: MAX_RESULTS,
  }
}
