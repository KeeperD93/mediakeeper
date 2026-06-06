import { ref } from 'vue'
import { useApi } from '@/composables/useApi'
import { useRequestStatus } from '@/composables/portal/useRequestStatus'
import { REQUEST_SORT } from '@/constants/requests'
import { DEFAULT_PAGE_SIZE } from '@/constants/pagination'

export function usePortalRequests() {
  const { apiGet, apiPost, apiPut, apiDelete, loading, error } = useApi()
  const { markStatus, invalidate } = useRequestStatus()
  const requests = ref([])
  const quota = ref(null)
  const total = ref(0)

  // Admin queue: offset pagination + server-side sort/filter so the toolbar
  // acts on the whole set, not just the loaded page.
  async function fetchAdminRequests({
    status = null,
    page = 1,
    perPage = DEFAULT_PAGE_SIZE,
    sort = REQUEST_SORT.RECENT,
    mediaType = null,
  } = {}) {
    const params = new URLSearchParams({ page, per_page: perPage, sort })
    if (status) params.set('status', status)
    if (mediaType) params.set('type', mediaType)
    try {
      const res = await apiGet(`/api/portal/requests/admin?${params}`)
      if (!res) return
      requests.value = res.items || []
      total.value = res.total || 0
    } catch {
      // Backend may not be migrated yet — fail to an empty list.
      requests.value = []
      total.value = 0
    }
  }

  async function createRequest(data) {
    return await apiPost('/api/portal/requests', data)
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
    total,
    fetchAdminRequests,
    createRequest,
    updateRequestStatus,
    deleteRequest,
    fetchQuota,
    loading,
    error,
  }
}
