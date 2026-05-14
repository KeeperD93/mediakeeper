/**
 * Coverage for the shared 429 helper.
 *
 * Two surfaces matter:
 *
 *   1. ``parseRetryAfter`` — must accept both shapes the spec allows
 *      (delta-seconds integer OR HTTP date) and refuse anything else
 *      so the caller falls back to the generic message.
 *   2. ``buildRateLimitMessage`` — must pick the right i18n key based
 *      on whether ``Retry-After`` was parseable. Pinning the key
 *      names here catches a typo on either side of the locale file.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

vi.mock('@/i18n', () => ({
  default: {
    global: {
      t: (key, named) => {
        if (named && Object.keys(named).length > 0) {
          return `${key}:${JSON.stringify(named)}`
        }
        return key
      },
    },
  },
}))

const showToast = vi.fn()
vi.mock('@/composables/useToast', () => ({
  useToast: () => ({ showToast }),
}))

import {
  parseRetryAfter,
  buildRateLimitMessage,
  showRateLimitToast,
  _resetRateLimitToastDedupe,
} from '@/composables/handle429'

describe('parseRetryAfter', () => {
  it('parses a positive integer of seconds', () => {
    expect(parseRetryAfter('30')).toBe(30)
    expect(parseRetryAfter('  30  ')).toBe(30)
    expect(parseRetryAfter('0')).toBe(0)
  })

  it('parses an HTTP date roughly seconds from now', () => {
    const future = new Date(Date.now() + 45_000).toUTCString()
    const seconds = parseRetryAfter(future)
    expect(seconds).not.toBeNull()
    // Allow a small margin: parsing + clock drift.
    expect(seconds).toBeGreaterThanOrEqual(43)
    expect(seconds).toBeLessThanOrEqual(46)
  })

  it('returns null on a past HTTP date', () => {
    const past = new Date(Date.now() - 60_000).toUTCString()
    expect(parseRetryAfter(past)).toBeNull()
  })

  it('returns null on missing / empty / unparseable input', () => {
    expect(parseRetryAfter(null)).toBeNull()
    expect(parseRetryAfter('')).toBeNull()
    expect(parseRetryAfter('   ')).toBeNull()
    expect(parseRetryAfter('not-a-date')).toBeNull()
    expect(parseRetryAfter('-5')).toBeNull()
  })
})

describe('buildRateLimitMessage', () => {
  it('uses the retry key with the seconds named arg when known', () => {
    expect(buildRateLimitMessage(45)).toBe('common.apiError.rate_limited_retry:{"seconds":45}')
  })

  it('falls back to the generic key when retry-after is missing', () => {
    expect(buildRateLimitMessage(null)).toBe('common.apiError.rate_limited')
  })

  it('falls back to the generic key when retry-after is zero or negative', () => {
    expect(buildRateLimitMessage(0)).toBe('common.apiError.rate_limited')
    expect(buildRateLimitMessage(-1)).toBe('common.apiError.rate_limited')
  })
})

describe('showRateLimitToast — 10 s dedupe window', () => {
  beforeEach(() => {
    showToast.mockReset()
    _resetRateLimitToastDedupe()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  function buildResponse(retryAfter) {
    const headers = new Headers()
    if (retryAfter !== undefined) headers.set('Retry-After', String(retryAfter))
    return new Response(null, { status: 429, headers })
  }

  it('collapses identical bursts into a single toast', () => {
    const res = buildResponse()
    for (let i = 0; i < 5; i += 1) showRateLimitToast(res)
    expect(showToast).toHaveBeenCalledTimes(1)
  })

  it('re-arms once the cooldown window elapses', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-05-15T10:00:00Z'))

    const res = buildResponse()
    showRateLimitToast(res)
    expect(showToast).toHaveBeenCalledTimes(1)

    // 10 s + 1 ms later — past the cooldown threshold.
    vi.setSystemTime(new Date('2026-05-15T10:00:10.001Z'))
    showRateLimitToast(res)
    expect(showToast).toHaveBeenCalledTimes(2)
  })

  it('does not dedupe when the message differs (Retry-After changes)', () => {
    showRateLimitToast(buildResponse(30))
    showRateLimitToast(buildResponse(60))
    expect(showToast).toHaveBeenCalledTimes(2)
  })
})
