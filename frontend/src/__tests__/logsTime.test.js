import { describe, it, expect } from 'vitest'
import { formatFileDate, formatLogLine } from '@/utils/logsTime'

// Tests pin ``timeZone`` (and ``locale`` where it changes the
// separator/order) via the opts argument so the assertions stay stable
// regardless of where CI runs.

describe('formatFileDate', () => {
  it('renders 12:41Z as 14:41 in Europe/Paris (CEST, +02:00)', () => {
    const out = formatFileDate('2026-05-08T12:41:00Z', {
      locale: 'fr-FR',
      timeZone: 'Europe/Paris',
    })
    expect(out).toContain('14:41')
    expect(out).toContain('08/05/2026')
  })

  it('renders 12:41Z as 12:41 in UTC', () => {
    const out = formatFileDate('2026-05-08T12:41:00Z', {
      locale: 'fr-FR',
      timeZone: 'UTC',
    })
    expect(out).toContain('12:41')
  })

  it('returns an empty string for invalid input so the caller can fall back', () => {
    expect(formatFileDate('')).toBe('')
    expect(formatFileDate(null)).toBe('')
    expect(formatFileDate(undefined)).toBe('')
    expect(formatFileDate('not-a-date')).toBe('')
  })

  it('accepts a Date instance', () => {
    const out = formatFileDate(new Date('2026-05-08T12:41:00Z'), {
      locale: 'fr-FR',
      timeZone: 'Europe/Paris',
    })
    expect(out).toContain('14:41')
  })
})

describe('formatLogLine — text form', () => {
  it('rewrites a leading "YYYY-MM-DD HH:mm:ss" UTC stamp into Europe/Paris', () => {
    const raw = '2026-05-08 12:41:00 [INFO] [mediakeeper.api] hello world'
    expect(formatLogLine(raw, { timeZone: 'Europe/Paris' })).toBe(
      '2026-05-08 14:41:00 [INFO] [mediakeeper.api] hello world',
    )
  })

  it('preserves the leading stamp byte-for-byte in UTC', () => {
    const raw = '2026-05-08 12:41:00 [DEBUG] [mediakeeper.api] tick'
    expect(formatLogLine(raw, { timeZone: 'UTC' })).toBe(raw)
  })

  it('handles DST winter (CET, +01:00)', () => {
    const raw = '2026-01-15 23:30:00 [WARNING] cold'
    expect(formatLogLine(raw, { timeZone: 'Europe/Paris' })).toBe(
      '2026-01-16 00:30:00 [WARNING] cold',
    )
  })

  it('returns the line unchanged when no timestamp is present', () => {
    const raw = 'no timestamp here'
    expect(formatLogLine(raw, { timeZone: 'Europe/Paris' })).toBe(raw)
  })

  it('only converts the leading stamp, not other digits later in the line', () => {
    const raw = '2026-05-08 12:41:00 [INFO] response in 12:41 ms'
    expect(formatLogLine(raw, { timeZone: 'Europe/Paris' })).toBe(
      '2026-05-08 14:41:00 [INFO] response in 12:41 ms',
    )
  })
})

describe('formatLogLine — JSON form', () => {
  it('rewrites the "ts" field while keeping the rest of the JSON intact', () => {
    const raw =
      '{"ts": "2026-05-08T12:41:00.123Z", "level": "INFO", "logger": "mediakeeper.api", "msg": "hello"}'
    const out = formatLogLine(raw, { timeZone: 'Europe/Paris' })
    expect(out).toContain('"ts": "2026-05-08 14:41:00"')
    expect(out).toContain('"level": "INFO"')
    expect(out).toContain('"logger": "mediakeeper.api"')
    expect(out).toContain('"msg": "hello"')
  })

  it('keeps level/module markers parseable after conversion', () => {
    const raw = '{"ts": "2026-05-08T12:41:00Z", "level": "ERROR", "logger": "mediakeeper.auth"}'
    const out = formatLogLine(raw, { timeZone: 'Europe/Paris' })
    expect(out.match(/"level"\s*:\s*"(\w+)"/)?.[1]).toBe('ERROR')
    expect(out.match(/"logger"\s*:\s*"mediakeeper\.([a-z_.]+)"/)?.[1]).toBe('auth')
  })
})

describe('formatLogLine — defensive', () => {
  it('passes through non-string input untouched', () => {
    expect(formatLogLine(null)).toBeNull()
    expect(formatLogLine(undefined)).toBeUndefined()
    expect(formatLogLine('')).toBe('')
  })
})
