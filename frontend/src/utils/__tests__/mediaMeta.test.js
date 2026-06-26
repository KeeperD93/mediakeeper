import { describe, it, expect } from 'vitest'
import {
  formatBytes,
  formatDuration,
  formatBitrate,
  hdrLabel,
  channelsLabel,
  languageLabel,
} from '../mediaMeta'

// Fake i18n: echo the key back when unknown (vue-i18n's default), so the
// code-path fallbacks (languageLabel uppercase, etc.) can be exercised.
const I18N = {
  'mediaManager.channels.mono': 'Mono',
  'mediaManager.channels.stereo': 'Stéréo',
  'mediaManager.languages.fr': 'Français',
  'mediaManager.languages.en': 'Anglais',
}
const t = (key, params) =>
  key === 'mediaManager.channels.count' ? `${params.n} ch` : (I18N[key] ?? key)

describe('formatBytes', () => {
  it('returns empty for 0 / falsy', () => {
    expect(formatBytes(0)).toBe('')
    expect(formatBytes(undefined)).toBe('')
  })
  it('localizes unit and number', () => {
    expect(formatBytes(1073741824, 'en')).toContain('GB')
    expect(formatBytes(1073741824, 'fr')).toContain('Go')
    expect(formatBytes(1048576, 'en')).toContain('MB')
  })
})

describe('formatDuration', () => {
  it('formats h/m/s and drops empty hours', () => {
    expect(formatDuration(3661)).toBe('1h 01m 01s')
    expect(formatDuration(61)).toBe('1m 01s')
    expect(formatDuration(0)).toBe('')
  })
})

describe('formatBitrate', () => {
  it('converts bps to kbps', () => {
    expect(formatBitrate(128000, 'en')).toBe('128 kbps')
    expect(formatBitrate(0)).toBe('')
  })
})

describe('hdrLabel', () => {
  it('maps known slugs and passes through the rest', () => {
    expect(hdrLabel('dolby_vision')).toBe('Dolby Vision')
    expect(hdrLabel('hdr10_plus')).toBe('HDR10+')
    expect(hdrLabel('')).toBe('')
    expect(hdrLabel('weird')).toBe('weird')
  })
})

describe('channelsLabel', () => {
  it('maps known layouts, falls back to a count', () => {
    expect(channelsLabel(1, t)).toBe('Mono')
    expect(channelsLabel(2, t)).toBe('Stéréo')
    expect(channelsLabel(6, t)).toBe('5.1')
    expect(channelsLabel(8, t)).toBe('7.1')
    expect(channelsLabel(7, t)).toBe('7 ch')
    expect(channelsLabel(0, t)).toBe('')
  })
})

describe('languageLabel', () => {
  it('localizes known codes, upper-cases unknown ones', () => {
    expect(languageLabel('fr', t)).toBe('Français')
    expect(languageLabel('bre', t)).toBe('BRE')
    expect(languageLabel('', t)).toBe('')
  })
})
