import { ref } from 'vue'
import { useApi } from '@/composables/useApi'

export function usePortalEvents() {
  const { apiGet, apiPost, loading, error } = useApi()
  const events = ref([])
  const parties = ref([])

  async function fetchActiveEvents() {
    const res = await apiGet('/api/portal/events/seasonal')
    if (res) events.value = res.items
  }

  async function getEventProgress(eventId) {
    return await apiGet(`/api/portal/events/seasonal/${eventId}/progress`)
  }

  async function createEvent(data) {
    return await apiPost('/api/portal/events/seasonal', data)
  }

  async function fetchParties() {
    const res = await apiGet('/api/portal/events/parties')
    if (res) parties.value = res.items
  }

  async function createParty(data) {
    return await apiPost('/api/portal/events/parties', data)
  }

  async function joinParty(partyId) {
    return await apiPost(`/api/portal/events/parties/${partyId}/join`)
  }

  async function leaveParty(partyId) {
    return await apiPost(`/api/portal/events/parties/${partyId}/leave`)
  }

  return {
    events,
    parties,
    fetchActiveEvents,
    getEventProgress,
    createEvent,
    fetchParties,
    createParty,
    joinParty,
    leaveParty,
    loading,
    error,
  }
}
