import { ref } from 'vue'
import { useApi } from '@/composables/useApi'
import { useRequestStatus } from '@/composables/portal/useRequestStatus'

export function usePortalRequests() {
  const { apiGet, apiPost, apiPut, apiDelete, loading, error } = useApi()
  const { markStatus, invalidate } = useRequestStatus()
  const requests = ref([])
  const quota = ref(null)
  const hasMore = ref(false)
  const nextCursor = ref(null)

  async function fetchRequests(status = null, reset = true, options = {}) {
    const { admin = false } = options
    if (reset) {
      requests.value = []
      nextCursor.value = null
    }
    let url = admin ? '/api/portal/requests/admin?limit=25' : '/api/portal/requests?limit=25'
    if (status) url += `&status=${status}`
    if (nextCursor.value) url += `&cursor=${nextCursor.value}`

    try {
      const res = await apiGet(url)
      if (!res) return
      if (reset) {
        requests.value = res.items || []
      } else {
        requests.value.push(...(res.items || []))
      }
      nextCursor.value = res.next_cursor
      hasMore.value = res.has_more
    } catch {
      // Backend may not be migrated yet — fail silently
      if (reset) requests.value = []
    }
  }

  async function createRequest(data) {
    return await apiPost('/api/portal/requests', data)
  }

  async function fetchAdminRequests(status = null, reset = true) {
    return fetchRequests(status, reset, { admin: true })
  }

  async function updateRequestStatus(requestId, status, reason = null) {
    const res = await apiPut(`/api/portal/requests/${requestId}/status`, { status, reason })
    // Patch the batch-status cache so the home / profile grids reflect the
    // new state immediately rather than waiting for the 30 s TTL — fixes
    // the "statut desync accueil ↔ profil" bug.
    const target = requests.value.find(r => r.id === requestId)
    if (target?.tmdb_id) {
      markStatus(target.tmdb_id, status, { request_id: requestId })
    }
    return res
  }

  async function deleteRequest(requestId) {
    const target = requests.value.find(r => r.id === requestId)
    const res = await apiDelete(`/api/portal/requests/${requestId}`)
    // Drop the row from local state + invalidate the batch-status cache
    // so the user can re-submit a fresh request immediately.
    requests.value = requests.value.filter(r => r.id !== requestId)
    if (target?.tmdb_id) invalidate(target.tmdb_id)
    return res
  }

  async function fetchQuota() {
    try {
      quota.value = await apiGet('/api/portal/requests/quota')
    } catch {
      quota.value = null
    }
  }

  return {
    requests,
    quota,
    hasMore,
    nextCursor,
    fetchRequests,
    fetchAdminRequests,
    createRequest,
    updateRequestStatus,
    deleteRequest,
    fetchQuota,
    loading,
    error,
  }
}
