import { ref, computed } from 'vue'
import { useApi } from '@/composables/useApi'

// Module-level state so the bell badge stays in sync across every
// component that imports the composable. Polled every 30 s; can be
// refreshed manually after an action that creates a notification.
const items = ref([])
const unread = ref(0)
const loading = ref(false)
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

  async function fetchList(unreadOnly = false) {
    loading.value = true
    try {
      const res = await apiGet(`/api/portal/notifications?unread_only=${unreadOnly}`)
      items.value = res?.items || []
    } finally {
      loading.value = false
    }
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
    fetchCount,
    fetchList,
    markRead,
    markAllRead,
    startPolling,
    stopPolling,
    hasUnread: computed(() => unread.value > 0),
  }
}
