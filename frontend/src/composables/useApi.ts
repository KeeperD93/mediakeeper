import { ref, type Ref } from 'vue'
import i18n from '@/i18n'
import { fetchApiResponse, type ApiFetchOptions } from './apiClient'
import { showRateLimitToast } from './handle429'

export { buildApiHeaders, fetchApiResponse, getCsrfToken } from './apiClient'
export type { ApiFetchOptions } from './apiClient'

/**
 * Translate a backend error code into a user-facing string.
 *
 * Backend endpoints return ``detail`` as a snake_case code
 * (``invalid_credentials``, ``backup_not_found``, …). When the code
 * exists under ``common.apiError.*`` we resolve it; otherwise we
 * surface the raw code so developers can spot gaps quickly.
 */
export function resolveApiError(code?: string | null): string {
  // i18n.global.t has overloaded signatures — treat it as a narrow
  // (key: string, named?: Record<string, unknown>) => string shape
  // because that's the only form this module uses.
  const t = i18n.global.t as unknown as (key: string, named?: Record<string, unknown>) => string
  if (!code) return t('common.apiError.unknown', { status: '' })
  const key = `common.apiError.${code}`
  const localized = t(key)
  return localized === key ? code : localized
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
 * Composable for les calls API with management automatique
 * du cookie httpOnly JWT et redirection 401.
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
        if (res.status === 429) {
          // Surface the rate-limit response as a friendly toast before
          // the throw — the calling component can still react via its
          // own catch block, but the user already has a visible hint.
          showRateLimitToast(res)
        }
        const data = await res.json().catch(() => ({}))
        throw new Error(data.detail || `http_${res.status}`)
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
   * Raccourci GET JSON
   */
  async function apiGet<T = unknown>(url: string): Promise<T | null> {
    const res = await apiFetch(url)
    return res ? ((await res.json()) as T) : null
  }

  /**
   * Raccourci POST JSON
   */
  async function apiPost<T = unknown, B = unknown>(url: string, body?: B): Promise<T | null> {
    const res = await apiFetch(url, {
      method: 'POST',
      body: JSON.stringify(body),
    })
    return res ? ((await res.json()) as T) : null
  }

  /**
   * Raccourci PUT JSON
   */
  async function apiPut<T = unknown, B = unknown>(url: string, body?: B): Promise<T | null> {
    const res = await apiFetch(url, {
      method: 'PUT',
      body: JSON.stringify(body),
    })
    return res ? ((await res.json()) as T) : null
  }

  /**
   * Raccourci DELETE
   */
  async function apiDelete<T = unknown>(url: string): Promise<T | null> {
    const res = await apiFetch(url, { method: 'DELETE' })
    return res ? ((await res.json()) as T) : null
  }

  /**
   * Raccourci PATCH JSON
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
