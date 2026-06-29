import { ref, readonly } from 'vue'
import { fetchApiResponse, useApi } from '@/composables/useApi'
import { showRateLimitToast } from '@/composables/handle429'

const profile = ref(null)
const isPortalAuth = ref(false)
const unreadNewsCount = ref(0)
const ui = ref({ show_requests_tab: true })
// GDPR opt-in state from /auth/me — drives the Privacy tab visibility
// (``enabled``) and the grace-period banner (``pending_deletion_at``).
// Stays null until the first /auth/me call lands.
const gdpr = ref(null)

const DEFAULT_GDPR = {
  enabled: false,
  deletion_requested_at: null,
  pending_deletion_at: null,
}

export function usePortalAuth() {
  const { apiPut, loading, error } = useApi()

  function setPortalAuth(nextProfile, unreadCount = 0, nextUi = null, nextGdpr = null) {
    profile.value = nextProfile
    isPortalAuth.value = !!nextProfile
    unreadNewsCount.value = unreadCount
    ui.value = { show_requests_tab: true, ...(nextUi || {}) }
    gdpr.value = nextGdpr ? { ...DEFAULT_GDPR, ...nextGdpr } : null
  }

  async function portalAuthFetch(url, options = {}) {
    error.value = null
    loading.value = true

    try {
      const res = await fetchApiResponse(url, {
        ...options,
        retryOn401: false,
        redirectOn401: false,
      })
      if (!res) return { ok: false, status: 0, data: null }

      if (res.status === 429) {
        showRateLimitToast(res)
      }

      let data = null
      try {
        data = await res.json()
      } catch {
        data = null
      }

      return { ok: res.ok, status: res.status, data }
    } catch (e) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function checkPortalAuth() {
    try {
      const res = await portalAuthFetch('/api/portal/auth/me')
      if (res.ok && res.data?.profile) {
        setPortalAuth(res.data.profile, res.data.unread_news_count || 0, res.data.ui, res.data.gdpr)
        return true
      }
    } catch {
      // Not authenticated for portal
    }
    clearPortalAuth()
    return false
  }

  async function refreshAuth() {
    // Re-pull /auth/me so consumers see the updated ``gdpr`` block
    // (after a deletion-request submit / cancel) without forcing a
    // full ``checkPortalAuth`` reset path.
    try {
      const res = await portalAuthFetch('/api/portal/auth/me')
      if (res.ok && res.data?.profile) {
        setPortalAuth(res.data.profile, res.data.unread_news_count || 0, res.data.ui, res.data.gdpr)
        return true
      }
    } catch {
      // Silent — caller falls back to the existing state.
    }
    return false
  }

  async function updateProfile(data) {
    const res = await apiPut('/api/portal/profiles/me', data)
    if (res) profile.value = res
    return res
  }

  function clearPortalAuth() {
    profile.value = null
    isPortalAuth.value = false
    ui.value = { show_requests_tab: true }
    gdpr.value = null
  }

  return {
    profile: readonly(profile),
    ui: readonly(ui),
    gdpr: readonly(gdpr),
    isPortalAuth: readonly(isPortalAuth),
    unreadNewsCount: readonly(unreadNewsCount),
    checkPortalAuth,
    refreshAuth,
    updateProfile,
    setPortalAuth,
    clearPortalAuth,
    loading,
    error,
  }
}
