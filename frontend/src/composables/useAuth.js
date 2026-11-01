import { ref, readonly } from 'vue'
import { fetchApiResponse } from '@/composables/useApi'
import { extractDetailCode } from '@/composables/apiClient'
import { parseRetryAfter, rateLimitCode } from '@/composables/handle429'
import { STORAGE_KEYS } from '@/constants/storage'

const user = ref(null)
const isAuthenticated = ref(false)
const mustChangePassword = ref(false)

let refreshInterval = null

/**
 * Authentication composable.
 * Global state shared across all components.
 */
export function useAuth() {
  /**
   * Check the JWT cookie via /api/auth/me
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

    let data
    try {
      const text = await res.text()
      data = text ? JSON.parse(text) : {}
    } catch {
      if (res.status === 503) throw new Error('starting')
      throw new Error('unexpected')
    }

    if (res.status === 503) {
      throw new Error(extractDetailCode(data, 'starting'))
    }

    if (res.status === 429) {
      // A refused sign-in keeps its reason and its wait; anything else is the toast.
      const refused = new Error(rateLimitCode(res, data))
      refused.retryAfter = parseRetryAfter(res.headers.get('Retry-After'))
      throw refused
    }

    if (!res.ok) {
      // A server failure is not a wrong password.
      const fallback = res.status >= 500 ? `http_${res.status}` : 'invalid_credentials'
      throw new Error(extractDetailCode(data, fallback))
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
      usePortalAuth().setPortalAuth(data.profile, data.unread_news_count || 0, data.ui)
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
    } catch {
      /* ignore */
    }
    try {
      sessionStorage.setItem(STORAGE_KEYS.JUST_LOGGED_OUT, '1')
    } catch {
      /* ignore */
    }
    user.value = null
    isAuthenticated.value = false
    stopTokenRefresh()
    // Also wipe the in-memory Portal state — the backend logout
    // already clears rq_token server-side, but the composable keeps
    // a module-scoped ref that survives page transitions.
    try {
      const { usePortalAuth } = await import('@/composables/portal/usePortalAuth')
      usePortalAuth().clearPortalAuth()
    } catch {
      /* composable may not be loaded yet */
    }
  }

  /**
   * Refresh the JWT cookie every 25 min
   */
  function startTokenRefresh() {
    stopTokenRefresh()

    // Immediate refresh
    fetchApiResponse('/api/auth/refresh', {
      method: 'POST',
      retryOn401: false,
      redirectOn401: false,
    }).catch(() => {})

    // Refresh every 25 min
    refreshInterval = setInterval(
      () => {
        fetchApiResponse('/api/auth/refresh', {
          method: 'POST',
          retryOn401: false,
          redirectOn401: false,
        }).catch(() => {})
      },
      25 * 60 * 1000,
    )

    // Refresh when the tab regains focus
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
   * Change password
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

    // A proxy page is not JSON: as an error it reads as its bare status, and
    // as a "success" it proves nothing, so it is not one.
    const data = await res.json().catch(() => null)
    if (res.status === 429) throw new Error(rateLimitCode(res, data))
    if (!res.ok) throw new Error(extractDetailCode(data, `http_${res.status}`))
    if (!data) throw new Error('unexpected')

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
