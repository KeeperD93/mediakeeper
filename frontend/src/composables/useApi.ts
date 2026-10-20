import { ref, type Ref } from 'vue'
import i18n from '@/i18n'
import {
  RATE_LIMITED_NOTIFIED,
  extractDetailCode,
  fetchApiResponse,
  type ApiFetchOptions,
} from './apiClient'
import { rateLimitCode } from './handle429'

export { buildApiHeaders, fetchApiResponse, getCsrfToken } from './apiClient'
export type { ApiFetchOptions } from './apiClient'

// A bare HTTP status, kept when an answer carried no code (``http_502``).
const HTTP_STATUS_CODE = /^http_(\d{3})$/

/**
 * Translate a backend error code into a user-facing string.
 *
 * Backend endpoints return ``detail`` as a snake_case code
 * (``invalid_credentials``, ``backup_not_found``, …). When the code
 * exists under ``common.apiError.*`` we resolve it. Otherwise the
 * caller's own message names what failed (``fallbackKey``: "Could not
 * create the backup"), whatever the cause: a status without a code, a
 * request that never got an answer. Without one, a bare status
 * (``http_502``) reads "Error 502" and any other code is surfaced raw
 * so developers can spot gaps quickly. A rate limit, already shown by
 * its own toast, resolves to '' (showToast then stays silent).
 */
export function resolveApiError(code?: string | null, fallbackKey?: string): string {
  // i18n.global.t has overloaded signatures — treat it as a narrow
  // (key: string, named?: Record<string, unknown>) => string shape
  // because that's the only form this module uses.
  const t = i18n.global.t as unknown as (key: string, named?: Record<string, unknown>) => string
  if (code === RATE_LIMITED_NOTIFIED) return ''
  if (code) {
    const key = `common.apiError.${code}`
    const localized = t(key)
    if (localized !== key) return localized
  }
  if (fallbackKey) return t(fallbackKey)
  if (!code) return t('common.apiError.unknown', { status: '' })
  const status = HTTP_STATUS_CODE.exec(code)?.[1]
  return status ? t('common.apiError.unknown', { status }) : code
}

/**
 * A screen's own message for an error code (``portal.lists.errors.list_full``)
 * when its locale scope has one, else ``resolveApiError``. Bare statuses skip
 * the scope: where one words them, it is about another service (Emby).
 */
export function resolveScopedError(
  scope: string,
  code?: string | null,
  fallbackKey?: string,
): string {
  const t = i18n.global.t as unknown as (key: string) => string
  if (code && !HTTP_STATUS_CODE.test(code)) {
    const key = `${scope}.${code}`
    const localized = t(key)
    if (localized !== key) return localized
  }
  return resolveApiError(code, fallbackKey)
}

export interface UseApiReturn {
  apiFetch: (url: string, options?: ApiFetchOptions) => Promise<Response | null>
  apiGet: <T = unknown>(url: string) => Promise<T | null>
  apiPost: <T = unknown, B = unknown>(url: string, body?: B) => Promise<T | null>
  apiPut: <T = unknown, B = unknown>(url: string, body?: B) => Promise<T | null>
  apiDelete: <T = unknown>(url: string) => Promise<T | null>
  apiPatch: <T = unknown, B = unknown>(url: string, body?: B) => Promise<T | null>
  loading: Ref<boolean>
  error: Ref<string | null>
}

/**
 * API calls with the httpOnly JWT cookie sent automatically: a 401 renews
 * the session once, then redirects to the login page.
 */
export function useApi(): UseApiReturn {
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function apiFetch(url: string, options: ApiFetchOptions = {}): Promise<Response | null> {
    error.value = null
    loading.value = true

    try {
      const res = await fetchApiResponse(url, options)
      if (!res) {
        return null
      }

      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        if (res.status === 429) throw new Error(rateLimitCode(res, data))
        throw new Error(extractDetailCode(data, `http_${res.status}`))
      }

      return res
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e)
      throw e
    } finally {
      loading.value = false
    }
  }

  /**
   * GET shortcut returning the parsed JSON.
   */
  async function apiGet<T = unknown>(url: string): Promise<T | null> {
    const res = await apiFetch(url)
    return res ? ((await res.json()) as T) : null
  }

  /**
   * POST shortcut with a JSON body.
   */
  async function apiPost<T = unknown, B = unknown>(url: string, body?: B): Promise<T | null> {
    const res = await apiFetch(url, {
      method: 'POST',
      body: JSON.stringify(body),
    })
    return res ? ((await res.json()) as T) : null
  }

  /**
   * PUT shortcut with a JSON body.
   */
  async function apiPut<T = unknown, B = unknown>(url: string, body?: B): Promise<T | null> {
    const res = await apiFetch(url, {
      method: 'PUT',
      body: JSON.stringify(body),
    })
    return res ? ((await res.json()) as T) : null
  }

  /**
   * DELETE shortcut.
   */
  async function apiDelete<T = unknown>(url: string): Promise<T | null> {
    const res = await apiFetch(url, { method: 'DELETE' })
    return res ? ((await res.json()) as T) : null
  }

  /**
   * PATCH shortcut with a JSON body.
   */
  async function apiPatch<T = unknown, B = unknown>(url: string, body?: B): Promise<T | null> {
    const res = await apiFetch(url, {
      method: 'PATCH',
      body: JSON.stringify(body),
    })
    return res ? ((await res.json()) as T) : null
  }

  return { apiFetch, apiGet, apiPost, apiPut, apiDelete, apiPatch, loading, error }
}
