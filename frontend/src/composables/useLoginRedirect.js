import { ref } from 'vue'
import { NavigationFailureType, isNavigationFailure, useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuth } from '@/composables/useAuth'
import { fetchApiResponse } from '@/composables/useApi'
import { STORAGE_KEYS } from '@/constants/storage'

/**
 * Login-page startup flow: wait for the backend to answer, then resolve an
 * already-valid session. An authenticated admin/portal visitor is redirected
 * straight to their destination; everyone else stays on the form with the
 * saved username pre-filled and the logged-out / session-expired banners
 * surfaced. After a sign-in, it leaves for the same destinations. Owns only the
 * startup-flow state — the form inputs stay in the component, which passes the
 * refs this flow writes into.
 */
export function useLoginRedirect({ username, remember, errorMsg, loggedOutMsg, submitting }) {
  const route = useRoute()
  const router = useRouter()
  const { t } = useI18n()
  const { checkAuth, mustChangePassword } = useAuth()

  const backendReady = ref(false)
  const appVersion = ref('')
  let loggedOutTimer = null

  function getRedirectTarget() {
    return typeof route.query.redirect === 'string' ? route.query.redirect : ''
  }

  // Where a signed-in visitor goes: a member to the portal, an admin back where the
  // sign-in was asked for.
  function destination(isMember) {
    const redirect = getRedirectTarget()
    if (isMember) return redirect.startsWith('/portal') ? redirect : '/portal'
    return redirect || '/'
  }

  // A temporary password is changed on the dashboard first.
  function targetAfterSignIn(data) {
    if (data.scope === 'portal') return destination(true)
    if (data.must_change_password) return '/?force_change_password=1'
    return destination(false)
  }

  // The redirect comes from the address bar: a full load never leaves this site, and
  // one too broken to read goes to the home page rather than nowhere.
  function loadInFull(target) {
    let href = '/'
    try {
      const url = new URL(router.resolve(target).href, window.location.origin)
      if (url.origin === window.location.origin) href = url.href
    } catch (err) {
      console.error('[useLoginRedirect.loadInFull]', err)
    }
    window.location.assign(href)
  }

  /**
   * Leaves for where a sign-in leads. `submitting` stays true while the page is
   * left: a press during that navigation would sign in a second time. Only a
   * navigation that ends back here, or throws, frees it.
   */
  async function leaveAfterSignIn(data) {
    const target = targetAfterSignIn(data)
    const stopWatching = () => {
      stopOnEnd()
      stopOnError()
    }
    const stopOnEnd = router.afterEach((to, from, failure) => {
      // Cancelled: a newer navigation took over, and its own end decides.
      if (isNavigationFailure(failure, NavigationFailureType.cancelled)) return
      stopWatching()
      if (router.currentRoute.value.name === 'login') submitting.value = false
    })
    // A navigation that throws never reaches the hook above, and the page stays.
    const stopOnError = router.onError(() => {
      stopWatching()
      submitting.value = false
    })
    try {
      await router.push(target)
    } catch (err) {
      // Signed in, but the next page could not load here (files replaced by an update):
      // load it from the server, busy again until then (the error hook freed it).
      console.error('[useLoginRedirect.leaveAfterSignIn]', err)
      submitting.value = true
      loadInFull(target)
    }
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

  // Runs after the network checks: a password manager may have filled the field
  // meanwhile, and overwriting only its name would pair it with the wrong password.
  function prefillSavedUsername() {
    const saved = localStorage.getItem(STORAGE_KEYS.SAVED_USERNAME)
    if (!saved) return
    remember.value = true
    if (!username.value) username.value = saved
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
      // A temporary password is changed on the dashboard first: a page that needs
      // the portal would refuse the admin and send them straight back here.
      if (mustChangePassword.value) {
        router.replace('/')
        return
      }
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
      router.replace(destination(false))
      return
    }

    try {
      const { usePortalAuth } = await import('@/composables/portal/usePortalAuth')
      const ok = await usePortalAuth().checkPortalAuth()
      if (ok) {
        router.replace(destination(true))
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

  return { backendReady, appVersion, getRedirectTarget, leaveAfterSignIn, start, dispose }
}
