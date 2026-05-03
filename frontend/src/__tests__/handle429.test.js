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
import { describe, it, expect, vi } from 'vitest'

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

import { parseRetryAfter, buildRateLimitMessage } from '@/composables/handle429'

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
    expect(buildRateLimitMessage(45)).toBe(
      'common.apiError.rate_limited_retry:{"seconds":45}',
    )
  })

  it('falls back to the generic key when retry-after is missing', () => {
    expect(buildRateLimitMessage(null)).toBe('common.apiError.rate_limited')
  })

  it('falls back to the generic key when retry-after is zero or negative', () => {
    expect(buildRateLimitMessage(0)).toBe('common.apiError.rate_limited')
    expect(buildRateLimitMessage(-1)).toBe('common.apiError.rate_limited')
  })
})
