import { ref, readonly } from 'vue'
import { fetchApiResponse, useApi } from '@/composables/useApi'

const profile = ref(null)
const isPortalAuth = ref(false)
const unreadNewsCount = ref(0)
const ui = ref({ show_requests_tab: true })

export function usePortalAuth() {
  const { apiPut, loading, error } = useApi()

  function setPortalAuth(nextProfile, unreadCount = 0, nextUi = null) {
    profile.value = nextProfile
    isPortalAuth.value = !!nextProfile
    unreadNewsCount.value = unreadCount
    ui.value = { show_requests_tab: true, ...(nextUi || {}) }
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

  async function portalLogin(username, password) {
    const res = await portalAuthFetch('/api/portal/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    })
    if (res.ok && res.data?.success) {
      setPortalAuth(
        res.data.profile,
        res.data.unread_news?.length || 0,
        res.data.ui,
      )
      return res.data
    }
    return null
  }

  async function checkPortalAuth() {
    try {
      const res = await portalAuthFetch('/api/portal/auth/me')
      if (res.ok && res.data?.profile) {
        setPortalAuth(
          res.data.profile,
          res.data.unread_news_count || 0,
          res.data.ui,
        )
        return true
      }
    } catch {
      // Not authenticated for portal
    }
    clearPortalAuth()
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
  }

  return {
    profile: readonly(profile),
    ui: readonly(ui),
    isPortalAuth: readonly(isPortalAuth),
    unreadNewsCount: readonly(unreadNewsCount),
    portalLogin,
    checkPortalAuth,
    updateProfile,
    setPortalAuth,
    clearPortalAuth,
    loading,
    error,
  }
}
