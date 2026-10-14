import { describe, it, expect } from 'vitest'
import { canRequest } from '@/utils/portal/requestEligibility'

describe('canRequest', () => {
  it('allows a title nobody requested yet', () => {
    expect(canRequest(null, null)).toBe(true)
    expect(canRequest(undefined, 'partial')).toBe(true)
  })

  it('allows a new request after a rejection', () => {
    expect(canRequest('rejected', null)).toBe(true)
  })

  it('freezes a pending or approved request', () => {
    expect(canRequest('pending', 'partial')).toBe(false)
    expect(canRequest('approved', null)).toBe(false)
  })

  it('allows a served series that still misses episodes', () => {
    expect(canRequest('available', 'partial')).toBe(true)
  })

  it('refuses a served title that is complete or not indexed', () => {
    expect(canRequest('available', 'full')).toBe(false)
    expect(canRequest('available', null)).toBe(false)
  })

  it('refuses a blacklisted title', () => {
    expect(canRequest('blacklisted', 'partial')).toBe(false)
  })
})
