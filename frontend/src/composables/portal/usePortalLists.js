import { ref } from 'vue'
import { useApi } from '@/composables/useApi'

export function usePortalLists() {
  const { apiFetch, apiGet, apiPost, apiPatch, apiDelete, loading, error } = useApi()

  const lists = ref([])
  const publicLists = ref([])
  const publicTotal = ref(0)
  const publicHasMore = ref(false)
  const publicCursor = ref(null)
  const moderationLists = ref([])
  const moderationTotal = ref(0)
  const moderationHasMore = ref(false)
  const moderationCursor = ref(null)
  const currentList = ref(null)
  const history = ref([])

  // Drop rows already present (by id) when appending a "load more" page. The
  // keyset cursor avoids overlap; this is the display-side safety net.
  function _dedupById(items) {
    const seen = new Set()
    return items.filter(it => !seen.has(it.id) && seen.add(it.id))
  }

  async function fetchMyLists() {
    const res = await apiGet('/api/portal/lists')
    if (res) lists.value = res.items || []
    return lists.value
  }

  async function fetchPublicLists({ limit = 50, cursor = null, append = false } = {}) {
    const qs = cursor ? `?limit=${limit}&cursor=${encodeURIComponent(cursor)}` : `?limit=${limit}`
    const res = await apiGet(`/api/portal/lists/public${qs}`)
    const items = res?.items || []
    publicLists.value = append ? _dedupById([...publicLists.value, ...items]) : items
    publicTotal.value = res?.total ?? publicLists.value.length
    publicHasMore.value = !!res?.has_more
    publicCursor.value = res?.next_cursor || null
    return res
  }

  // Admin moderation feed: includes soft-deleted lists (require_admin).
  async function fetchModerationLists({ limit = 50, cursor = null, append = false } = {}) {
    const qs = cursor ? `?limit=${limit}&cursor=${encodeURIComponent(cursor)}` : `?limit=${limit}`
    const res = await apiGet(`/api/portal/admin/lists${qs}`)
    const items = res?.items || []
    moderationLists.value = append ? _dedupById([...moderationLists.value, ...items]) : items
    moderationTotal.value = res?.total ?? moderationLists.value.length
    moderationHasMore.value = !!res?.has_more
    moderationCursor.value = res?.next_cursor || null
    return res
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
    publicTotal,
    publicHasMore,
    publicCursor,
    moderationLists,
    moderationTotal,
    moderationHasMore,
    moderationCursor,
    currentList,
    history,
    fetchMyLists,
    fetchPublicLists,
    fetchModerationLists,
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
