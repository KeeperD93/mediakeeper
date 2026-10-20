/**
 * Shared 429 handling: the server's own reason when it gives one, else one
 * warning toast.
 *
 * Used where the app reads API answers itself:
 *   - ``useApi.apiFetch`` — every authenticated call
 *   - ``useAuth`` — sign-in and password change (``fetchApiResponse`` direct)
 *   - ``usePortalAuth.portalAuthFetch`` — the portal session check
 *
 * Keeping the logic in one place stops these branches drifting apart and
 * keeps the i18n contract (``common.apiError.rate_limited`` / ``..._retry``)
 * easy to grep.
 */
import i18n from '@/i18n'
import { TOAST_TYPE } from '@/constants/toast'
import { RATE_LIMITED_NOTIFIED } from './apiClient'
import { useToast } from './useToast'

/**
 * Parse the ``Retry-After`` header into a positive integer of seconds.
 *
 * The spec allows two shapes — an integer "delta-seconds" and an HTTP
 * date. We honour both; anything else (missing, NaN, past date) falls
 * back to ``null`` so the caller can surface a generic message.
 */
export function parseRetryAfter(raw: string | null): number | null {
  if (!raw) return null
  const trimmed = raw.trim()
  if (!trimmed) return null

  // delta-seconds form: a non-negative integer
  if (/^\d+$/.test(trimmed)) {
    const seconds = Number(trimmed)
    return Number.isFinite(seconds) && seconds >= 0 ? Math.ceil(seconds) : null
  }

  // HTTP date form: parse as UTC, compute the delta from now
  const ts = Date.parse(trimmed)
  if (Number.isNaN(ts)) return null
  const seconds = Math.ceil((ts - Date.now()) / 1000)
  return seconds > 0 ? seconds : null
}

/**
 * Build the i18n message that goes into the toast. Exposed for tests
 * so the contract can be pinned without rendering the full toast UI.
 */
export function buildRateLimitMessage(retryAfterSeconds: number | null): string {
  // i18n.global.t accepts (key, named) — type-narrowed to that shape
  // so the named-args form is what we get back.
  const t = i18n.global.t as unknown as (
    key: string,
    named?: Record<string, unknown>,
  ) => string
  if (retryAfterSeconds && retryAfterSeconds > 0) {
    return t('common.apiError.rate_limited_retry', { seconds: retryAfterSeconds })
  }
  return t('common.apiError.rate_limited')
}

// Slightly longer than the default 5 s: the operator usually waits and
// retries, and a too-fast dismiss steals the hint.
const TOAST_MS = 8000

/**
 * Surface a 429 response as a single warning toast.
 *
 * Caller responsibilities:
 *   - Only invoke when ``res.status === 429`` (no internal guard so
 *     the call site stays explicit).
 *   - Prefer ``rateLimitCode``, which only shows this toast when the
 *     server gave no reason of its own.
 *
 * Outside a Vue component (early bootstrap), the toast still lands in the
 * module-scoped store, and ``App.vue`` shows it once mounted.
 */
export function showRateLimitToast(res: Response): void {
  const message = buildRateLimitMessage(parseRetryAfter(res.headers.get('Retry-After')))
  const { toasts, showToast } = useToast()
  // A burst of parallel calls (the portal home) crosses the limit at once:
  // one toast while it is on screen, a new one once it has gone or was closed.
  if (toasts.value.some(toast => toast.message === message)) return
  showToast(message, TOAST_TYPE.WARN, TOAST_MS)
}

/**
 * The error code of a 429 answer. The server's own reason when it gives one
 * (``login_blocked``, a list's ``rate_limited``) is the caller's to show;
 * without one, the shared toast is the message and the caller gets
 * ``RATE_LIMITED_NOTIFIED``, which ``resolveApiError`` turns into nothing.
 */
export function rateLimitCode(res: Response, data: unknown): string {
  const detail = (data as { detail?: unknown } | null)?.detail
  if (typeof detail === 'string' && detail) return detail
  showRateLimitToast(res)
  return RATE_LIMITED_NOTIFIED
}
