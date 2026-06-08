import { ref, computed } from 'vue'
import { useApi } from '@/composables/useApi'

// Module-level state so the bell badge stays in sync across every
// component that imports the composable. Polled every 30 s; can be
// refreshed manually after an action that creates a notification.
const items = ref([])
const unread = ref(0)
const loading = ref(false)
const loadingMore = ref(false)
const nextCursor = ref(null)
const hasMore = ref(false)
let activeUnreadOnly = false
let pollTimer = null

export function useNotifications() {
  const { apiGet, apiPost } = useApi()

  async function fetchCount() {
    try {
      const res = await apiGet('/api/portal/notifications/count')
      unread.value = res?.unread || 0
    } catch {
      /* silent */
    }
  }

  // First page replaces the list; ``append`` keyset-loads the next page and
  // appends older notifications (bell "load more").
  async function fetchList(unreadOnly = false, append = false) {
    if (append && (!hasMore.value || loadingMore.value)) return
    if (append) loadingMore.value = true
    else {
      loading.value = true
      activeUnreadOnly = unreadOnly
    }
    try {
      const params = new URLSearchParams({
        unread_only: append ? activeUnreadOnly : unreadOnly,
      })
      if (append && nextCursor.value) params.set('cursor', nextCursor.value)
      const res = await apiGet(`/api/portal/notifications?${params}`)
      const list = res?.items || []
      items.value = append ? [...items.value, ...list] : list
      nextCursor.value = res?.next_cursor || null
      hasMore.value = !!res?.has_more
    } finally {
      if (append) loadingMore.value = false
      else loading.value = false
    }
  }

  function loadMore() {
    return fetchList(activeUnreadOnly, true)
  }

  async function markRead(id) {
    try {
      await apiPost(`/api/portal/notifications/${id}/read`)
      const it = items.value.find(n => n.id === id)
      if (it) it.read = true
      if (unread.value > 0) unread.value -= 1
    } catch {
      /* silent */
    }
  }

  async function markAllRead() {
    try {
      await apiPost('/api/portal/notifications/read-all')
      items.value.forEach(n => {
        n.read = true
      })
      unread.value = 0
    } catch {
      /* silent */
    }
  }

  function startPolling(intervalMs = 30000) {
    stopPolling()
    fetchCount()
    pollTimer = setInterval(fetchCount, intervalMs)
  }
  function stopPolling() {
    if (pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }
  }

  return {
    items,
    unread,
    loading,
    loadingMore,
    hasMore,
    fetchCount,
    fetchList,
    loadMore,
    markRead,
    markAllRead,
    startPolling,
    stopPolling,
    hasUnread: computed(() => unread.value > 0),
  }
}
