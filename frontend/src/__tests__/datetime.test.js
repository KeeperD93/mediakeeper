import { describe, it, expect, vi } from 'vitest'

vi.mock('@/i18n', () => ({ getLocale: () => 'en-US' }))

import { localizedDate, localizedTime, localizedDateTime } from '@/utils/datetime'

describe('datetime utils', () => {
  it('formats a Date with the active app locale (not the browser default)', () => {
    const d = new Date('2026-06-15T13:05:00')
    expect(localizedDate(d, { month: 'long' })).toBe(
      d.toLocaleDateString('en-US', { month: 'long' }),
    )
    expect(localizedTime(d, { hour: '2-digit', minute: '2-digit' })).toBe(
      d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
    )
    expect(localizedDateTime(d, { dateStyle: 'short' })).toBe(
      d.toLocaleString('en-US', { dateStyle: 'short' }),
    )
  })

  it('accepts a raw value and builds the Date itself', () => {
    expect(localizedDate('2026-06-15T00:00:00', { year: 'numeric' })).toBe(
      new Date('2026-06-15T00:00:00').toLocaleDateString('en-US', { year: 'numeric' }),
    )
  })
})
