import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { formatAgo } from '@/utils/formatAgo'

// Minimal translator: the unit short labels the util reads, echoed back.
const t = key =>
  ({
    'healthCheck.justNow': 'now',
    'stats.daysShort': 'd',
    'stats.monthsShort': 'mo',
    'stats.yearsShort': 'y',
  })[key] || key

const DAY = 86_400_000
const REF = new Date('2025-06-15T12:00:00Z')
const ago = days => REF.getTime() - days * DAY

describe('formatAgo', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(REF)
  })
  afterEach(() => {
    vi.useRealTimers()
  })

  it('returns an empty string for missing or unparsable input', () => {
    expect(formatAgo(null, t)).toBe('')
    expect(formatAgo(undefined, t)).toBe('')
    expect(formatAgo('not-a-date', t)).toBe('')
  })

  it('returns an empty string for a future timestamp', () => {
    expect(formatAgo(REF.getTime() + DAY, t)).toBe('')
  })

  it('formats sub-day distances (just-now, minutes, hours)', () => {
    expect(formatAgo(REF.getTime() - 30_000, t)).toBe('now')
    expect(formatAgo(REF.getTime() - 5 * 60_000, t)).toBe('5min')
    expect(formatAgo(REF.getTime() - 3 * 3_600_000, t)).toBe('3h')
  })

  it('compact (default) caps at days and never rolls up', () => {
    expect(formatAgo(ago(10), t)).toBe('10d')
    expect(formatAgo(ago(90), t)).toBe('90d')
    expect(formatAgo(ago(400), t)).toBe('400d')
  })

  it('verbose rolls days into months (30-364d) then years (>=365d)', () => {
    expect(formatAgo(ago(10), t, { style: 'verbose' })).toBe('10d')
    expect(formatAgo(ago(30), t, { style: 'verbose' })).toBe('1mo')
    expect(formatAgo(ago(90), t, { style: 'verbose' })).toBe('3mo')
    expect(formatAgo(ago(364), t, { style: 'verbose' })).toBe('12mo')
    expect(formatAgo(ago(365), t, { style: 'verbose' })).toBe('1y')
    expect(formatAgo(ago(730), t, { style: 'verbose' })).toBe('2y')
  })

  it('accepts Unix seconds and ISO strings', () => {
    expect(formatAgo(Math.floor(ago(5) / 1000), t)).toBe('5d')
    expect(formatAgo(new Date(ago(5)).toISOString(), t)).toBe('5d')
  })
})
