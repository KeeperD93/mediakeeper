import { ref } from 'vue'
import { useApi } from '@/composables/useApi'
import { DEFAULT_PAGE_SIZE } from '@/constants/pagination'

export function usePortalTickets() {
  const { apiGet, apiPost, apiPut, loading, error } = useApi()
  const tickets = ref([])
  const currentTicket = ref(null)
  const total = ref(0)

  // Offset pagination + server-side status/type/sort filtering. ``sort`` is
  // left to the backend default (newest) when the caller omits it.
  async function fetchTickets({
    status = null,
    issueTypes = null,
    sort = null,
    page = 1,
    perPage = DEFAULT_PAGE_SIZE,
  } = {}) {
    const qs = new URLSearchParams({ page, per_page: perPage })
    if (sort) qs.set('sort', sort)
    if (status) qs.set('status', status)
    if (issueTypes?.length) qs.set('issue_type', issueTypes.join(','))
    try {
      const res = await apiGet(`/api/portal/tickets?${qs}`)
      if (!res) return
      tickets.value = res.items || []
      total.value = res.total || 0
    } catch {
      tickets.value = []
      total.value = 0
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
    tickets,
    currentTicket,
    total,
    fetchTickets,
    fetchTicket,
    createTicket,
    replyTicket,
    updateStatus,
    loading,
    error,
  }
}
