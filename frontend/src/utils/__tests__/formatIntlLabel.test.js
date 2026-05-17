import { describe, expect, it } from 'vitest'
import { formatCountry, formatLanguage } from '@/utils/formatIntlLabel'

describe('formatLanguage', () => {
  it('localises an ISO 639-1 code in French', () => {
    expect(formatLanguage('en', 'fr')).toBe('anglais')
    expect(formatLanguage('fr', 'fr')).toBe('français')
    expect(formatLanguage('ja', 'fr')).toBe('japonais')
  })

  it('localises an ISO 639-1 code in English', () => {
    expect(formatLanguage('en', 'en')).toBe('English')
    expect(formatLanguage('fr', 'en')).toBe('French')
    expect(formatLanguage('ja', 'en')).toBe('Japanese')
  })

  it('normalises the input casing', () => {
    expect(formatLanguage('EN', 'en')).toBe('English')
  })

  it('returns an empty string for falsy input', () => {
    expect(formatLanguage('', 'fr')).toBe('')
    expect(formatLanguage(null, 'fr')).toBe('')
    expect(formatLanguage(undefined, 'fr')).toBe('')
  })
})

describe('formatCountry', () => {
  it('localises an ISO 3166-1 alpha-2 code in French', () => {
    expect(formatCountry('US', 'fr')).toBe('États-Unis')
    expect(formatCountry('FR', 'fr')).toBe('France')
    expect(formatCountry('JP', 'fr')).toBe('Japon')
  })

  it('localises an ISO 3166-1 alpha-2 code in English', () => {
    expect(formatCountry('US', 'en')).toBe('United States')
    expect(formatCountry('FR', 'en')).toBe('France')
    expect(formatCountry('JP', 'en')).toBe('Japan')
  })

  it('normalises the input casing', () => {
    expect(formatCountry('us', 'fr')).toBe('États-Unis')
  })

  it('returns an empty string for falsy input', () => {
    expect(formatCountry('', 'fr')).toBe('')
    expect(formatCountry(null, 'fr')).toBe('')
    expect(formatCountry(undefined, 'fr')).toBe('')
  })
})
