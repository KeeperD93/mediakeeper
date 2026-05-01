const SAFE_METHODS = new Set<string>(['GET', 'HEAD', 'OPTIONS'])

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
  return readCookie('mk_csrf')
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

  return headers
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
  const canRetry = retryOn401 && url !== '/api/auth/refresh'

  if (res.status !== 401 || !canRetry) {
    if (res.status === 401 && redirectOn401) {
      window.location.href = '/login'
      return null
    }
    return res
  }

  const refreshRes = await runFetch('/api/auth/refresh', { method: 'POST' })
  if (!refreshRes.ok) {
    if (redirectOn401) {
      window.location.href = '/login'
      return null
    }
    return res
  }

  const retryRes = await runFetch(url)
  if (retryRes.status === 401 && redirectOn401) {
    window.location.href = '/login'
    return null
  }

  return retryRes
}
