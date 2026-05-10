import { describe, it, expect } from 'vitest'
import { extractYear } from '@/composables/mediaManagerHelpers'

describe('extractYear', () => {
  it('extracts year from "Title (YYYY)" pattern', () => {
    expect(extractYear('Dune (2023).mkv')).toBe('2023')
  })

  it('extracts year from dotted releases', () => {
    expect(extractYear('Dune.2023.1080p.WEB.mkv')).toBe('2023')
  })

  it('extracts year next to bracketed quality tags', () => {
    expect(extractYear('Movie 1999 [BluRay].mp4')).toBe('1999')
  })

  it('returns null when no year is present', () => {
    expect(extractYear('Plain Title.mkv')).toBe(null)
  })

  it('returns null for years outside 1900-2099 (low)', () => {
    expect(extractYear('Year out of range 1850.mp4')).toBe(null)
  })

  it('returns null for years outside 1900-2099 (high)', () => {
    expect(extractYear('Year out of range 2150.mp4')).toBe(null)
  })

  it('returns the first match when several candidate years are present', () => {
    expect(extractYear('Multiple 2010 and 2015.mkv')).toBe('2010')
  })
})
