import { ref } from 'vue'
import { useApi } from '@/composables/useApi'

export function usePortalTickets() {
  const { apiGet, apiPost, apiPut, loading, error } = useApi()
  const tickets = ref([])
  const currentTicket = ref(null)
  const hasMore = ref(false)
  const nextCursor = ref(null)

  async function fetchTickets(filters = {}, reset = true) {
    if (reset) {
      tickets.value = []
      nextCursor.value = null
    }
    const qs = new URLSearchParams({ limit: '25' })
    if (filters.status) qs.set('status', filters.status)
    if (filters.media_type?.length) qs.set('media_type', filters.media_type.join(','))
    if (filters.issue_type?.length) qs.set('issue_type', filters.issue_type.join(','))
    if (nextCursor.value) qs.set('cursor', nextCursor.value)

    try {
      const res = await apiGet(`/api/portal/tickets?${qs.toString()}`)
      if (!res) return
      if (reset) tickets.value = res.items || []
      else tickets.value.push(...(res.items || []))
      nextCursor.value = res.next_cursor
      hasMore.value = res.has_more
    } catch {
      if (reset) tickets.value = []
    }
  }

  async function fetchTicket(id) {
    try {
      currentTicket.value = await apiGet(`/api/portal/tickets/${id}`)
    } catch {
      currentTicket.value = null
    }
  }

  async function createTicket(data) {
    return await apiPost('/api/portal/tickets', data)
  }

  async function replyTicket(ticketId, content) {
    return await apiPost(`/api/portal/tickets/${ticketId}/reply`, { content })
  }

  async function updateStatus(ticketId, status) {
    return await apiPut(`/api/portal/tickets/${ticketId}/status`, { status })
  }

  return {
    tickets, currentTicket, hasMore, nextCursor,
    fetchTickets, fetchTicket, createTicket, replyTicket, updateStatus,
    loading, error,
  }
}
