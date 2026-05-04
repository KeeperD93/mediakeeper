import { ref } from 'vue'
import { useApi } from '@/composables/useApi'

export function usePortalAdmin() {
  const { apiGet, apiPost, apiPut, loading, error } = useApi()
  const stats = ref(null)

  async function fetchStats() {
    stats.value = await apiGet('/api/portal/admin/stats')
  }

  async function setQuota(userId, data) {
    return await apiPut(`/api/portal/admin/users/${userId}/quota`, data)
  }

  async function muteUser(userId, mutedUntil, reason = '') {
    return await apiPost(`/api/portal/admin/users/${userId}/mute`, {
      muted_until: mutedUntil,
      reason,
    })
  }

  async function unmuteUser(userId) {
    return await apiPost(`/api/portal/admin/users/${userId}/unmute`)
  }

  return {
    stats,
    fetchStats,
    setQuota,
    muteUser,
    unmuteUser,
    loading,
    error,
  }
}
