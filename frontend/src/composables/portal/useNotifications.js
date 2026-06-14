import { ref, computed } from 'vue'
import { useApi } from '@/composables/useApi'
import { useToast } from '@/composables/useToast'
import { TOAST_TYPE } from '@/constants/toast'
import i18n from '@/i18n'

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
  const { showToast } = useToast()

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
    // Block "load more" while the first page is still loading — stale paging
    // from a previous popup session must not fire a keyset request.
    if (append && (loading.value || !hasMore.value || loadingMore.value)) return
    if (append) loadingMore.value = true
    else {
      loading.value = true
      activeUnreadOnly = unreadOnly
      // Reset paging up front so a reopened popup never shows the previous
      // session's "load more" with a stale cursor before the GET resolves.
      hasMore.value = false
      nextCursor.value = null
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
    } catch (e) {
      console.error('[useNotifications.fetchList] failed', e)
      showToast(i18n.global.t('common.networkError'), TOAST_TYPE.ERR)
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

  // Clear the badge on open without flagging items read, so the list keeps
  // highlighting unread across all pages until close syncs the server.
  function clearUnreadBadge() {
    unread.value = 0
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
    clearUnreadBadge,
    startPolling,
    stopPolling,
    hasUnread: computed(() => unread.value > 0),
  }
}
