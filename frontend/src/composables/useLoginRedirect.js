import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuth } from '@/composables/useAuth'
import { fetchApiResponse } from '@/composables/useApi'
import { STORAGE_KEYS } from '@/constants/storage'

/**
 * Login-page startup flow: wait for the backend to answer, then resolve an
 * already-valid session. An authenticated admin/portal visitor is redirected
 * straight to their destination; everyone else stays on the form with the
 * saved username pre-filled and the logged-out / session-expired banners
 * surfaced. Owns only the startup-flow state — the form inputs stay in the
 * component, which passes the refs this flow writes into.
 */
export function useLoginRedirect({ username, remember, errorMsg, loggedOutMsg }) {
  const route = useRoute()
  const router = useRouter()
  const { t } = useI18n()
  const { checkAuth } = useAuth()

  const backendReady = ref(false)
  const appVersion = ref('')
  let loggedOutTimer = null

  function getRedirectTarget() {
    return typeof route.query.redirect === 'string' ? route.query.redirect : ''
  }

  async function waitForAuth() {
    while (true) {
      try {
        const res = await fetchApiResponse('/api/health', {
          retryOn401: false,
          redirectOn401: false,
        })
        if (res.status < 500) {
          backendReady.value = true
          return
        }
      } catch {
        /* silent: health poll retries by design */
      }
      await new Promise(r => setTimeout(r, 1500))
    }
  }

  async function fetchVersion() {
    try {
      const res = await fetchApiResponse('/api/changelog/current', {
        retryOn401: false,
        redirectOn401: false,
      })
      if (res.ok) {
        const data = await res.json()
        appVersion.value = data.version || ''
      }
    } catch {
      /* silent: version display is cosmetic */
    }
  }

  function prefillSavedUsername() {
    const saved = localStorage.getItem(STORAGE_KEYS.SAVED_USERNAME)
    if (saved) {
      username.value = saved
      remember.value = true
    }
  }

  async function resolveSession() {
    const justLoggedOut =
      route.query.logged_out === '1' || sessionStorage.getItem(STORAGE_KEYS.JUST_LOGGED_OUT) === '1'
    const sessionExpired = sessionStorage.getItem(STORAGE_KEYS.SESSION_EXPIRED) === '1'
    const redirect = getRedirectTarget()
    const isPortalRedirect = redirect.startsWith('/portal')
    const isPortalAdminRedirect = redirect.startsWith('/admin/portal') || isPortalRedirect

    if (justLoggedOut) {
      try {
        sessionStorage.removeItem(STORAGE_KEYS.JUST_LOGGED_OUT)
        sessionStorage.removeItem(STORAGE_KEYS.SESSION_EXPIRED)
      } catch {
        /* ignore */
      }
      loggedOutMsg.value = t('login.justLoggedOut')
      loggedOutTimer = setTimeout(() => {
        loggedOutMsg.value = ''
        loggedOutTimer = null
      }, 4000)
      fetchVersion()
      prefillSavedUsername()
      return
    }

    if (sessionExpired) {
      try {
        sessionStorage.removeItem(STORAGE_KEYS.SESSION_EXPIRED)
      } catch {
        /* ignore */
      }
      errorMsg.value = t('login.sessionExpired')
    }

    if (await checkAuth()) {
      if (redirect && isPortalAdminRedirect) {
        // Admin's mk_token survived but rq_token did not — re-issue the
        // portal session before honouring the deep-link so the destination
        // page doesn't immediately bounce back here.
        try {
          await fetchApiResponse('/api/portal/admin/requests/enter', {
            method: 'POST',
            retryOn401: false,
            redirectOn401: false,
          })
        } catch {
          /* best-effort — page-level guard will still surface a fresh 401 */
        }
      }
      router.replace(redirect || '/')
      return
    }

    try {
      const { usePortalAuth } = await import('@/composables/portal/usePortalAuth')
      const ok = await usePortalAuth().checkPortalAuth()
      if (ok) {
        router.replace(isPortalRedirect ? redirect : '/portal')
        return
      }
    } catch {
      // Stay on the login page if the portal check fails.
    }

    fetchVersion()
    prefillSavedUsername()
  }

  async function start() {
    await waitForAuth()
    await resolveSession()
  }

  function dispose() {
    if (loggedOutTimer) {
      clearTimeout(loggedOutTimer)
      loggedOutTimer = null
    }
  }

  return { backendReady, appVersion, getRedirectTarget, start, dispose }
}
