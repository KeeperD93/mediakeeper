/**
 * Shared 429 handler — surfaces the rate-limit response as a single
 * user-facing toast.
 *
 * Called from the three layers that hit the API:
 *   - ``useApi.apiFetch`` — every authenticated mutation / read
 *   - ``useAuth.login`` — admin login bootstrap (``fetchApiResponse`` direct)
 *   - ``usePortalAuth.portalAuthFetch`` — Emby portal login bootstrap
 *
 * Keeping the logic in one place avoids three near-identical
 * try-block branches drifting apart and makes the i18n contract
 * (``common.apiError.rate_limited`` / ``..._retry``) easy to grep.
 */
import i18n from '@/i18n'
import { TOAST_TYPE } from '@/constants/toast'
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

/**
 * Surface a 429 response as a single warning toast.
 *
 * Caller responsibilities:
 *   - Only invoke when ``res.status === 429`` (no internal guard so
 *     the call site stays explicit).
 *   - Keep throwing / propagating the original error after this call —
 *     the toast is informational, not flow control.
 *
 * If the user is not in a Vue component context (e.g. early bootstrap
 * before the toast subscriber mounts), the toast still queues into the
 * module-scoped store; ``GlobalToasts.vue`` flushes the backlog the
 * moment it mounts.
 */
// Module-scoped dedupe — the Portal home can fire several 429s back-to-back
// when a burst of parallel requests crosses the rate limit. Surfacing a
// fresh toast each time stacks identical warnings on the user; we collapse
// repeats of the *same* message inside a short cooldown window instead.
const TOAST_COOLDOWN_MS = 10_000
let lastToastTs = 0
let lastToastMessage: string | null = null

/** Test-only escape hatch — resets the module-scoped dedupe state so a
 *  test that asserts the cooldown does not bleed into the next one. */
export function _resetRateLimitToastDedupe(): void {
  lastToastTs = 0
  lastToastMessage = null
}

export function showRateLimitToast(res: Response): void {
  const retry = parseRetryAfter(res.headers.get('Retry-After'))
  const seconds = retry ?? null
  const message = buildRateLimitMessage(seconds)

  const now = Date.now()
  if (lastToastMessage === message && now - lastToastTs < TOAST_COOLDOWN_MS) {
    return
  }
  lastToastTs = now
  lastToastMessage = message

  const { showToast } = useToast()
  // Slightly longer than the default 5 s — the operator usually waits
  // and retries; a too-fast dismiss steals the hint.
  showToast(message, TOAST_TYPE.WARN, 8000)
}
