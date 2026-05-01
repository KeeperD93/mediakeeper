import { ref, computed, onUnmounted } from 'vue'
import { useApi } from '@/composables/useApi'
import { useAvailability } from './useAvailability'
import { useRequestStatus } from './useRequestStatus'

/**
 * Generic infinite scroll loader for the paginated /discover/category
 * and /discover/browse-provider endpoints.
 *
 * Usage:
 *   const { items, loading, hasMore, sort, setSort, loadMore, observe } =
 *     useInfiniteDiscover('/api/portal/catalog/category/movies')
 *
 * Then in the template:
 *   <div ref="sentinelRef" />   // observed by IntersectionObserver
 *   onMounted(() => observe(sentinelRef.value))
 *
 * Items are automatically de-duplicated by tmdb_id+media_type and have
 * their availability + request-status fetched on the fly so MediaCard
 * can show its dot, post-it badge and Playback / Demander button.
 */
export function useInfiniteDiscover(endpoint, { sort: initialSort = 'popularity' } = {}) {
  const { apiGet } = useApi()
  const { checkAvailability } = useAvailability()
  const { checkStatus: checkRequestStatus } = useRequestStatus()

  const items = ref([])
  const page = ref(0)
  const hasMore = ref(true)
  const loading = ref(false)
  const sort = ref(initialSort)
  const error = ref(null)

  const seen = new Set()
  let observer = null

  function reset() {
    items.value = []
    page.value = 0
    hasMore.value = true
    error.value = null
    seen.clear()
  }

  async function loadMore() {
    if (loading.value || !hasMore.value) return
    loading.value = true
    error.value = null
    try {
      const next = page.value + 1
      const sep = endpoint.includes('?') ? '&' : '?'
      const url = `${endpoint}${sep}page=${next}&sort=${sort.value}`
      const res = await apiGet(url)
      const fresh = (res?.items || []).filter((it) => {
        const key = `${it.media_type || 'movie'}:${it.tmdb_id || it.id}`
        if (seen.has(key)) return false
        seen.add(key)
        return true
      })
      items.value.push(...fresh)
      page.value = next
      hasMore.value = !!res?.has_more && fresh.length > 0
      // Best-effort enrichment so cards render with the right state.
      if (fresh.length) {
        await Promise.all([
          checkAvailability(fresh),
          checkRequestStatus(fresh),
        ])
      }
    } catch (e) {
      error.value = e
      hasMore.value = false
    } finally {
      loading.value = false
      // If after loading the sentinel is still visible (not enough items
      // to fill the viewport), automatically load the next page.
      if (hasMore.value && _sentinel && isElementInViewport(_sentinel)) {
        requestAnimationFrame(() => loadMore())
      }
    }
  }

  let _sentinel = null

  function isElementInViewport(el) {
    const rect = el.getBoundingClientRect()
    return rect.top < (window.innerHeight || document.documentElement.clientHeight) + 200
  }

  function setSort(newSort) {
    if (newSort === sort.value) return
    sort.value = newSort
    reset()
    loadMore()
  }

  /**
   * Wire an IntersectionObserver to a sentinel element. As soon as the
   * sentinel intersects the viewport (with a 200px lookahead margin),
   * loadMore() is fired. Repeated calls reuse the same observer.
   */
  function observe(el) {
    if (!el) return
    _sentinel = el
    if (observer) observer.disconnect()
    observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            loadMore()
          }
        }
      },
      { rootMargin: '200px 0px' },
    )
    observer.observe(el)
  }

  onUnmounted(() => {
    if (observer) observer.disconnect()
  })

  return {
    items,
    loading,
    hasMore,
    sort,
    setSort,
    loadMore,
    observe,
    reset,
    error,
    isEmpty: computed(() => !loading.value && items.value.length === 0),
  }
}
