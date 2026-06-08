import { STORAGE_KEYS } from '@/constants/storage'

const SAFE_METHODS = new Set<string>(['GET', 'HEAD', 'OPTIONS'])

const AUTH_REFRESH_URL = '/api/auth/refresh'
const PORTAL_ADMIN_ENTER_URL = '/api/portal/admin/requests/enter'
const CSRF_COOKIE = 'mk_csrf'

export interface ApiFetchOptions extends RequestInit {
  retryOn401?: boolean
  redirectOn401?: boolean
}

function readCookie(name: string): string {
  const prefix = `${name}=`
  return (
    document.cookie
      .split('; ')
      .find(cookie => cookie.startsWith(prefix))
      ?.slice(prefix.length) || ''
  )
}

export function getCsrfToken(): string {
  return readCookie(CSRF_COOKIE)
}

export function buildApiHeaders(options: ApiFetchOptions = {}): Headers {
  const method = (options.method || 'GET').toUpperCase()
  const headers = new Headers(options.headers || {})
  const isFormData = typeof FormData !== 'undefined' && options.body instanceof FormData

  if (!headers.has('Content-Type') && options.body !== undefined && !isFormData) {
    headers.set('Content-Type', 'application/json')
  }

  if (!SAFE_METHODS.has(method)) {
    const csrfToken = getCsrfToken()
    if (csrfToken) headers.set('X-CSRF-Token', csrfToken)
  }

  // Forward the viewer's active UI locale (global or portal-ephemeral) so the
  // backend can localize content per viewer. Read from <html lang> (kept in
  // sync by i18n) instead of importing i18n — i18n imports this module, so a
  // direct import would be circular.
  if (typeof document !== 'undefined') {
    const locale = document.documentElement.lang
    if (locale && !headers.has('X-MK-Locale')) headers.set('X-MK-Locale', locale)
  }

  return headers
}

function redirectToLogin(): null {
  try {
    sessionStorage.setItem(STORAGE_KEYS.SESSION_EXPIRED, '1')
  } catch {
    /* sessionStorage may be unavailable (private mode, SSR) — degrade silently */
  }
  const { pathname, search } = window.location
  const current = `${pathname}${search}`
  const skip = current === '/login' || current.startsWith('/login?')
  const target = skip ? '/login' : `/login?redirect=${encodeURIComponent(current)}`
  window.location.href = target
  return null
}

export async function fetchApiResponse(
  url: string,
  options: ApiFetchOptions = {},
): Promise<Response | null> {
  const { retryOn401 = true, redirectOn401 = true, ...fetchOptions } = options

  const runFetch = (target: string, nextOptions: ApiFetchOptions = fetchOptions) =>
    fetch(target, {
      credentials: 'include',
      ...nextOptions,
      headers: buildApiHeaders(nextOptions),
    })

  const res = await runFetch(url)
  const isSelfRefresh = url === AUTH_REFRESH_URL || url === PORTAL_ADMIN_ENTER_URL
  const canRetry = retryOn401 && !isSelfRefresh

  if (res.status !== 401 || !canRetry) {
    if (res.status === 401 && redirectOn401) {
      return redirectToLogin()
    }
    return res
  }

  const refreshRes = await runFetch(AUTH_REFRESH_URL, { method: 'POST' })
  if (!refreshRes.ok) {
    if (redirectOn401) {
      return redirectToLogin()
    }
    return res
  }

  const retryRes = await runFetch(url)

  // Portal admin routes use a separate ``rq_token`` cookie that
  // ``/api/auth/refresh`` does NOT renew. When the admin's portal
  // session has lapsed independently of mk_token, the retry still
  // 401s — re-issue rq_token via the existing admin bypass and try
  // once more before giving up. Skip if the call IS /enter to avoid
  // infinite loops.
  if (
    retryRes.status === 401
    && url.startsWith('/api/portal/')
    && url !== PORTAL_ADMIN_ENTER_URL
  ) {
    const enterRes = await runFetch(PORTAL_ADMIN_ENTER_URL, { method: 'POST' })
    if (enterRes.ok) {
      const finalRes = await runFetch(url)
      if (finalRes.status === 401 && redirectOn401) {
        return redirectToLogin()
      }
      return finalRes
    }
  }

  if (retryRes.status === 401 && redirectOn401) {
    return redirectToLogin()
  }

  return retryRes
}
