import { ref, readonly } from 'vue'
import { fetchApiResponse } from '@/composables/useApi'

const user = ref(null)
const isAuthenticated = ref(false)
const mustChangePassword = ref(false)

let refreshInterval = null

/**
 * Composable d'authentification.
 * State global shared entre all les components.
 */
export function useAuth() {

  /**
   * Check le cookie JWT via /api/auth/me
   */
  async function checkAuth() {
    try {
      const res = await fetchApiResponse('/api/auth/me', { redirectOn401: false })
      if (!res.ok) {
        user.value = null
        isAuthenticated.value = false
        return false
      }
      const data = await res.json()
      user.value = data
      isAuthenticated.value = true
      mustChangePassword.value = !!data.must_change_password
      return true
    } catch {
      user.value = null
      isAuthenticated.value = false
      return false
    }
  }

  /**
   * Login
   */
  async function login(username, password) {
    const res = await fetchApiResponse('/api/auth/portal-login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
      retryOn401: false,
      redirectOn401: false,
    })

    let data = {}
    try {
      const text = await res.text()
      data = text ? JSON.parse(text) : {}
    } catch {
      if (res.status === 503) throw new Error('starting')
      throw new Error('unexpected')
    }

    if (res.status === 503) {
      throw new Error(data.detail || 'starting')
    }

    if (!res.ok) {
      throw new Error(data.detail || 'invalid_credentials')
    }

    if (data.scope === 'admin') {
      user.value = data
      isAuthenticated.value = true
      mustChangePassword.value = !!data.must_change_password
      startTokenRefresh()
    } else {
      user.value = null
      isAuthenticated.value = false
      mustChangePassword.value = false
      stopTokenRefresh()
      const { usePortalAuth } = await import('@/composables/portal/usePortalAuth')
      usePortalAuth().setPortalAuth(
        data.profile,
        data.unread_news_count || 0,
        data.ui,
      )
    }

    return data
  }

  /**
   * Logout
   */
  async function logout() {
    try {
      await fetchApiResponse('/api/auth/logout', {
        method: 'POST',
        retryOn401: false,
        redirectOn401: false,
      })
    } catch { /* ignore */ }
    try {
      sessionStorage.setItem('mk_just_logged_out', '1')
    } catch { /* ignore */ }
    user.value = null
    isAuthenticated.value = false
    stopTokenRefresh()
      // Also wipe the in-memory Portal state — the backend logout
    // already clears rq_token server-side, but the composable keeps
    // a module-scoped ref that survives page transitions.
    try {
      const { usePortalAuth } = await import('@/composables/portal/usePortalAuth')
      usePortalAuth().clearPortalAuth()
    } catch { /* composable may not be loaded yet */ }
  }

  /**
   * Refresh JWT cookie all les 25 min
   */
  function startTokenRefresh() {
    stopTokenRefresh()

    // Refresh immediat
    fetchApiResponse('/api/auth/refresh', {
      method: 'POST',
      retryOn401: false,
      redirectOn401: false,
    }).catch(() => {})

    // Refresh all les 25 min
    refreshInterval = setInterval(() => {
      fetchApiResponse('/api/auth/refresh', {
        method: 'POST',
        retryOn401: false,
        redirectOn401: false,
      }).catch(() => {})
    }, 25 * 60 * 1000)

    // Refresh au retour sur l'tab
    document.addEventListener('visibilitychange', onVisibilityChange)
  }

  function stopTokenRefresh() {
    if (refreshInterval) {
      clearInterval(refreshInterval)
      refreshInterval = null
    }
    document.removeEventListener('visibilitychange', onVisibilityChange)
  }

  function onVisibilityChange() {
    if (document.visibilityState === 'visible') {
      fetchApiResponse('/api/auth/refresh', {
        method: 'POST',
        retryOn401: false,
        redirectOn401: false,
      }).catch(() => {})
    }
  }

  /**
   * Changement de mot de passe
   */
  async function changePassword(currentPassword, newPassword) {
    const body = JSON.stringify({
      current_password: currentPassword,
      new_password: newPassword,
      confirm_password: newPassword,
    })
    const res = await fetchApiResponse('/api/auth/change-password', {
      method: 'POST',
      body,
      redirectOn401: false,
    })

    const data = await res.json()
    if (!res.ok) throw new Error(data.detail || 'unknown')

    mustChangePassword.value = false
    return data
  }

  return {
    user: readonly(user),
    isAuthenticated: readonly(isAuthenticated),
    mustChangePassword: readonly(mustChangePassword),
    checkAuth,
    login,
    logout,
    changePassword,
    startTokenRefresh,
  }
}
