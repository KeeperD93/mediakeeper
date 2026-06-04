import { ref, onMounted, onUnmounted } from 'vue'
import { useApi } from '@/composables/useApi'
import { localizedDateTime } from '@/utils/datetime'

export function useTopbarAlerts() {
  const { apiGet, apiPost, apiDelete } = useApi()
  const alertCount = ref(0)
  const recentAlerts = ref([])
  const seenIds = ref(new Set())
  let alertTimer = null

  async function loadAlertCount() {
    try {
      const [alerts, seen, chatData] = await Promise.all([
        apiGet('/api/emby/alerts').catch(() => null),
        apiGet('/api/alerts/seen').catch(() => null),
        apiGet('/api/portal/admin/requests/chat/reports?only_open=true').catch(() => null),
      ])
      if (!alerts || !seen) return
      seenIds.value = new Set((seen.seen || []).map(String))

      const embyItems = (Array.isArray(alerts) ? alerts : []).slice(0, 10).map(a => ({
        kind: 'emby',
        id: a.id || a.date,
        name: a.name,
        date: a.date,
        raw: a,
      }))

      const chatItems = ((chatData && chatData.items) || []).map(r => ({
        kind: 'chat_report',
        id: `chat_report_${r.id}`,
        name: `Reported message: ${(r.message_content || '').slice(0, 80)}`,
        date: r.created_at,
        report_id: r.id,
        message_id: r.message_id,
        message_deleted: r.message_deleted,
        author_name: r.message_author_name,
      }))

      const merged = [...chatItems, ...embyItems]
        .sort((a, b) => new Date(b.date || 0) - new Date(a.date || 0))
        .slice(0, 10)
      recentAlerts.value = merged
      alertCount.value = merged.filter(a => !seenIds.value.has(String(a.id))).length
    } catch {
      /* silent: topbar alerts poll, retries on next tick */
    }
  }

  async function dismissChatReport(alert) {
    await apiPost(`/api/portal/admin/requests/chat/reports/${alert.report_id}/dismiss`, {}).catch(
      () => null,
    )
    await loadAlertCount()
  }

  async function deleteChatMessage(alert) {
    await apiDelete(`/api/portal/admin/requests/chat/messages/${alert.message_id}`).catch(
      () => null,
    )
    await loadAlertCount()
  }

  function isAlertSeen(alert) {
    return seenIds.value.has(String(alert.id || alert.date))
  }

  async function markAllRead() {
    for (const a of recentAlerts.value) {
      const id = String(a.id || a.date)
      if (!seenIds.value.has(id)) {
        seenIds.value.add(id)
        apiPost(`/api/alerts/seen/${encodeURIComponent(id)}`, {}).catch(() => null)
      }
    }
    seenIds.value = new Set(seenIds.value)
    alertCount.value = 0
  }

  function formatDate(dateStr) {
    if (!dateStr) return ''
    return localizedDateTime(new Date(dateStr), {
      day: '2-digit',
      month: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  onMounted(() => {
    loadAlertCount()
    alertTimer = setInterval(loadAlertCount, 30000)
  })
  onUnmounted(() => {
    if (alertTimer) clearInterval(alertTimer)
  })

  return {
    alertCount,
    recentAlerts,
    seenIds,
    loadAlertCount,
    dismissChatReport,
    deleteChatMessage,
    isAlertSeen,
    markAllRead,
    formatDate,
  }
}
