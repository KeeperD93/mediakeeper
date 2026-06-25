import { describe, it, expect } from 'vitest'
import {
  ticksToTime,
  ticksToHours,
  fmtSize,
  langLabel,
  langShort,
  parseTicks,
} from '../statsFormat'

const TICK = 1e7 // ticks per second

describe('ticksToTime', () => {
  it('formats h:mm:ss', () => {
    expect(ticksToTime(3600 * TICK)).toBe('1:00:00')
    expect(ticksToTime(5400 * TICK)).toBe('1:30:00')
    expect(ticksToTime(65 * TICK)).toBe('0:01:05')
    expect(ticksToTime(0)).toBe('0:00:00')
  })
})

describe('ticksToHours', () => {
  it('returns dash for falsy input', () => {
    expect(ticksToHours(0)).toBe('—')
  })
  it('omits the hour part under 1h', () => {
    expect(ticksToHours(1800 * TICK)).toBe('30min')
  })
  it('shows hours and minutes', () => {
    expect(ticksToHours(3600 * TICK)).toBe('1h 0min')
    expect(ticksToHours(5400 * TICK)).toBe('1h 30min')
  })
})

describe('fmtSize', () => {
  it('returns dash for falsy input', () => {
    expect(fmtSize(0)).toBe('—')
  })
  it('scales to TB / GB / MB', () => {
    expect(fmtSize(1099511627776)).toBe('1.00 TB')
    expect(fmtSize(2147483648)).toBe('2.00 GB')
    expect(fmtSize(5242880)).toBe('5.0 MB')
  })
})

describe('langLabel', () => {
  it('maps 2- and 3-letter codes case-insensitively', () => {
    expect(langLabel('fr')).toBe('French')
    expect(langLabel('FRE')).toBe('French')
    expect(langLabel('und')).toBe('Unknown')
  })
  it('falls back to uppercase for unknown codes, empty for blank', () => {
    expect(langLabel('xx')).toBe('XX')
    expect(langLabel('')).toBe('')
    expect(langLabel(null)).toBe('')
  })
})

describe('langShort', () => {
  it('maps known codes, empty otherwise', () => {
    expect(langShort('fr')).toBe('FR')
    expect(langShort('jpn')).toBe('JA')
    expect(langShort('xx')).toBe('')
    expect(langShort('')).toBe('')
  })
})

describe('parseTicks', () => {
  it('parses h:mm:ss back to ticks', () => {
    expect(parseTicks('1:00:00')).toBe(3600 * TICK)
    expect(parseTicks('0:01:05')).toBe(65 * TICK)
  })
  it('returns 0 for blank or malformed input', () => {
    expect(parseTicks('')).toBe(0)
    expect(parseTicks('bad')).toBe(0)
    expect(parseTicks(null)).toBe(0)
  })
})
