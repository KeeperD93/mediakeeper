import { describe, it, expect } from 'vitest'
import { extractDetailCode } from '@/composables/useAuth'

describe('extractDetailCode', () => {
  it('returns a non-empty string detail as-is', () => {
    expect(extractDetailCode({ detail: 'account_disabled' }, 'fallback')).toBe('account_disabled')
  })

  it('returns the fallback when detail is an empty string', () => {
    expect(extractDetailCode({ detail: '' }, 'invalid_credentials')).toBe('invalid_credentials')
  })

  it('returns "validation_failed" for a Pydantic 422 array payload', () => {
    const data = {
      detail: [{ type: 'missing', loc: ['body', 'username'], msg: 'Field required' }],
    }
    expect(extractDetailCode(data, 'invalid_credentials')).toBe('validation_failed')
  })

  it('falls back when detail is an empty array', () => {
    expect(extractDetailCode({ detail: [] }, 'fallback')).toBe('fallback')
  })

  it('falls back when data has no detail key', () => {
    expect(extractDetailCode({}, 'fallback')).toBe('fallback')
    expect(extractDetailCode(null, 'fallback')).toBe('fallback')
    expect(extractDetailCode(undefined, 'fallback')).toBe('fallback')
  })
})
