/**
 * API layer for the premium admin "Users" page.
 *
 * Every URL the new page calls lives here so the components stay
 * declarative and the path is editable in one spot when the backend
 * ever moves under a different prefix.
 */
import { useApi } from '@/composables/useApi'

const BASE = '/api/portal/admin/users'

export function usePortalAdminUsers() {
  const { apiGet, apiPost, apiPatch, apiDelete } = useApi()

  function buildQuery(params = {}) {
    const search = new URLSearchParams()
    for (const [key, value] of Object.entries(params)) {
      if (value === null || value === undefined || value === '') continue
      if (typeof value === 'boolean') {
        search.set(key, value ? 'true' : 'false')
        continue
      }
      search.set(key, String(value))
    }
    const qs = search.toString()
    return qs ? `?${qs}` : ''
  }

  async function fetchPresets() {
    return await apiGet(`${BASE}/role-presets`)
  }

  async function fetchStats() {
    return await apiGet(`${BASE}/stats`)
  }

  async function fetchTags() {
    return await apiGet(`${BASE}/tags`)
  }

  async function resetPassword(id) {
    return await apiPost(`${BASE}/${id}/reset-password`, {})
  }

  async function forceLogout(id) {
    return await apiPost(`${BASE}/${id}/force-logout`, {})
  }

  async function resetDisplayName(id) {
    return await apiPost(`${BASE}/${id}/reset-display-name`, {})
  }

  async function fetchLoginHistory(id, { limit = 100, cursor = null } = {}) {
    return await apiGet(`${BASE}/${id}/login-history${buildQuery({ limit, cursor })}`)
  }

  async function fetchUsers(params = {}) {
    return await apiGet(`${BASE}${buildQuery(params)}`)
  }

  async function fetchUser(id) {
    return await apiGet(`${BASE}/${id}`)
  }

  async function fetchActivity(id) {
    return await apiGet(`${BASE}/${id}/activity`)
  }

  async function fetchTrophies(id) {
    return await apiGet(`${BASE}/${id}/trophies`)
  }

  async function fetchXpHistory(id, { limit = 100, cursor = null } = {}) {
    return await apiGet(`${BASE}/${id}/xp-history${buildQuery({ limit, cursor })}`)
  }

  async function fetchUserRequests(id, { limit = 100, cursor = null } = {}) {
    return await apiGet(`${BASE}/${id}/requests${buildQuery({ limit, cursor })}`)
  }

  async function fetchUserTickets(id, { limit = 100, cursor = null } = {}) {
    return await apiGet(`${BASE}/${id}/tickets${buildQuery({ limit, cursor })}`)
  }

  async function fetchAudit(id, { limit = 100, cursor = null } = {}) {
    return await apiGet(`${BASE}/${id}/audit${buildQuery({ limit, cursor })}`)
  }

  async function patchIdentity(id, payload) {
    return await apiPatch(`${BASE}/${id}`, payload)
  }

  async function patchRole(id, role) {
    return await apiPatch(`${BASE}/${id}/role`, { role })
  }

  async function patchPermissions(id, permissions) {
    return await apiPatch(`${BASE}/${id}/permissions`, { permissions })
  }

  async function patchActive(id, active) {
    return await apiPatch(`${BASE}/${id}/active`, { active })
  }

  async function patchAccess(id, { start, end } = {}) {
    return await apiPatch(`${BASE}/${id}/access`, { start, end })
  }

  async function postExtendAccess(id, months) {
    return await apiPost(`${BASE}/${id}/extend-access`, { months })
  }

  async function postEmbyToggle(id, enabled) {
    return await apiPost(`${BASE}/${id}/emby-toggle`, { enabled })
  }

  async function patchNotes(id, notes) {
    return await apiPatch(`${BASE}/${id}/notes`, { notes })
  }

  async function patchTags(id, tags) {
    return await apiPatch(`${BASE}/${id}/tags`, { tags })
  }

  async function softDelete(id) {
    return await apiDelete(`${BASE}/${id}`)
  }

  async function restoreUser(id) {
    return await apiPost(`${BASE}/${id}/restore`, {})
  }

  async function exportUser(id) {
    return await apiGet(`${BASE}/${id}/export`)
  }

  function exportUserCsvUrl(id) {
    return `${BASE}/${id}/export?format=csv`
  }

  async function bulkAction({ action, profile_ids, payload = null }) {
    return await apiPost(`${BASE}/bulk`, { action, profile_ids, payload })
  }

  async function notifyUser(id, { title, body }) {
    return await apiPost(`${BASE}/${id}/notify`, { title, body })
  }

  async function fetchEmbyUnimported() {
    return await apiGet(`${BASE}/emby/unimported`)
  }

  async function syncEmbyIds() {
    return await apiPost(`${BASE}/emby/sync-ids`, {})
  }

  async function importEmbySelected(emby_user_ids) {
    return await apiPost(`${BASE}/emby/import`, { emby_user_ids })
  }

  async function createLocalUser(payload) {
    return await apiPost(`${BASE}/local`, payload)
  }

  return {
    fetchPresets,
    fetchStats,
    fetchTags,
    resetPassword,
    forceLogout,
    resetDisplayName,
    fetchLoginHistory,
    fetchUsers,
    fetchUser,
    fetchActivity,
    fetchTrophies,
    fetchXpHistory,
    fetchUserRequests,
    fetchUserTickets,
    fetchAudit,
    patchIdentity,
    patchRole,
    patchPermissions,
    patchActive,
    patchAccess,
    postExtendAccess,
    postEmbyToggle,
    patchNotes,
    patchTags,
    softDelete,
    restoreUser,
    exportUser,
    exportUserCsvUrl,
    bulkAction,
    notifyUser,
    fetchEmbyUnimported,
    syncEmbyIds,
    importEmbySelected,
    createLocalUser,
  }
}
