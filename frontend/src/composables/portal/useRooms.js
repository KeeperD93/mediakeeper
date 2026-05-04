import { ref } from 'vue'
import { useApi } from '@/composables/useApi'

// Module-level cache so the calendar list and the banner share state.
const events = ref([])
const loading = ref(false)

export function useRooms() {
  const { apiGet, apiPost, apiPatch, apiDelete } = useApi()

  async function fetchAll() {
    loading.value = true
    try {
      const res = await apiGet('/api/portal/events/rooms')
      events.value = res?.items || []
    } finally {
      loading.value = false
    }
  }

  async function getOne(id) {
    return apiGet(`/api/portal/events/rooms/${id}`)
  }

  async function create(payload) {
    const res = await apiPost('/api/portal/events/rooms', payload)
    if (res && !res.error) {
      events.value = [res, ...events.value]
    }
    return res
  }

  async function update(id, payload) {
    const res = await apiPatch(`/api/portal/events/rooms/${id}`, payload)
    if (res && !res.error) {
      const idx = events.value.findIndex(e => e.id === id)
      if (idx >= 0) events.value[idx] = res
    }
    return res
  }

  async function cancel(id) {
    const res = await apiDelete(`/api/portal/events/rooms/${id}`)
    if (res && !res.error) {
      events.value = events.value.filter(e => e.id !== id)
    }
    return res
  }

  async function respond(id, decision) {
    return apiPost(`/api/portal/events/rooms/${id}/respond`, { decision })
  }

  async function inviteUser(id, userId) {
    return apiPost(`/api/portal/events/rooms/${id}/invite/${userId}`)
  }

  async function removeMember(id, userId) {
    return apiPost(`/api/portal/events/rooms/${id}/remove/${userId}`)
  }

  async function enterRoom(id) {
    return apiPost(`/api/portal/events/rooms/${id}/enter`)
  }

  async function listMessages(id) {
    const res = await apiGet(`/api/portal/events/rooms/${id}/messages`)
    return res?.items || []
  }

  async function postMessage(id, content) {
    return apiPost(`/api/portal/events/rooms/${id}/messages`, { content })
  }

  async function searchUsers(q) {
    const res = await apiGet(`/api/portal/profiles/search/users?q=${encodeURIComponent(q)}`)
    return res?.items || []
  }

  return {
    events,
    loading,
    fetchAll,
    getOne,
    create,
    update,
    cancel,
    respond,
    inviteUser,
    removeMember,
    enterRoom,
    listMessages,
    postMessage,
    searchUsers,
  }
}
