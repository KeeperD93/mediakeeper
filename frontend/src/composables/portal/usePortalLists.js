import { ref } from 'vue'
import { useApi } from '@/composables/useApi'

export function usePortalLists() {
  const { apiFetch, apiGet, apiPost, apiPatch, apiDelete, loading, error } = useApi()

  const lists = ref([])
  const publicLists = ref([])
  const currentList = ref(null)
  const history = ref([])

  async function fetchMyLists() {
    const res = await apiGet('/api/portal/lists')
    if (res) lists.value = res.items || []
    return lists.value
  }

  async function fetchPublicLists(limit = 50) {
    const res = await apiGet(`/api/portal/lists/public?limit=${limit}`)
    if (res) publicLists.value = res.items || []
    return publicLists.value
  }

  async function fetchList(id, { sort = 'added_desc', page = 1, pageSize = 100 } = {}) {
    const res = await apiGet(
      `/api/portal/lists/${id}?sort=${sort}&page=${page}&page_size=${pageSize}`,
    )
    if (res) currentList.value = res
    return res
  }

  async function createList(data) {
    return await apiPost('/api/portal/lists', data)
  }

  async function updateList(id, data) {
    return await apiPatch(`/api/portal/lists/${id}`, data)
  }

  async function deleteList(id) {
    return await apiDelete(`/api/portal/lists/${id}`)
  }

  async function addItems(listId, items) {
    return await apiPost(`/api/portal/lists/${listId}/items`, { items })
  }

  async function removeItems(listId, { items, item_ids } = {}) {
    const res = await apiFetch(`/api/portal/lists/${listId}/items`, {
      method: 'DELETE',
      body: JSON.stringify({ items, item_ids }),
    })
    return res ? res.json() : null
  }

  async function moveItems(srcId, dstId, itemIds) {
    return await apiPost(`/api/portal/lists/${srcId}/move`, {
      dst_list_id: dstId,
      item_ids: itemIds,
    })
  }

  async function copyItems(srcId, dstId, itemIds) {
    return await apiPost(`/api/portal/lists/${srcId}/copy-items`, {
      dst_list_id: dstId,
      item_ids: itemIds,
    })
  }

  async function copyList(id, newName = null) {
    return await apiPost(`/api/portal/lists/${id}/copy`, { new_name: newName })
  }

  async function fetchHistory(id, limit = 100) {
    const res = await apiGet(`/api/portal/lists/${id}/history?limit=${limit}`)
    if (res) history.value = res.items || []
    return history.value
  }

  async function addContributor(listId, userId) {
    return await apiPost(`/api/portal/lists/${listId}/contributors`, { user_id: userId })
  }

  async function removeContributor(listId, userId) {
    return await apiDelete(`/api/portal/lists/${listId}/contributors/${userId}`)
  }

  function exportUrl(id, fmt = 'json') {
    return `/api/portal/lists/${id}/export?fmt=${fmt}`
  }

  // Admin
  async function adminUndelete(id) {
    return await apiPost(`/api/portal/admin/lists/${id}/undelete`)
  }

  async function adminHardDelete(id) {
    return await apiDelete(`/api/portal/admin/lists/${id}`)
  }

  async function adminMuteOwner(id, muted) {
    return await apiPost(`/api/portal/admin/lists/${id}/mute-owner`, { muted })
  }

  async function adminMuteContributor(listId, userId, muted) {
    return await apiPost(`/api/portal/admin/lists/${listId}/contributors/${userId}/mute`, { muted })
  }

  return {
    lists,
    publicLists,
    currentList,
    history,
    fetchMyLists,
    fetchPublicLists,
    fetchList,
    createList,
    updateList,
    deleteList,
    addItems,
    removeItems,
    moveItems,
    copyItems,
    copyList,
    fetchHistory,
    addContributor,
    removeContributor,
    exportUrl,
    adminUndelete,
    adminHardDelete,
    adminMuteOwner,
    adminMuteContributor,
    loading,
    error,
  }
}
