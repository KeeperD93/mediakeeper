/**
 * Covers buildApiHeaders forwarding the active UI locale as X-MK-Locale.
 * The locale is read from <html lang> (kept in sync by i18n) to avoid a
 * circular import; the backend uses it to localize content per viewer.
 */
import { describe, it, expect, afterEach } from 'vitest'
import { buildApiHeaders } from '@/composables/apiClient'

describe('buildApiHeaders — X-MK-Locale', () => {
  afterEach(() => {
    document.documentElement.lang = ''
  })

  it('forwards the active <html lang> as X-MK-Locale', () => {
    document.documentElement.lang = 'en'
    const h = buildApiHeaders({ method: 'GET' })
    expect(h.get('X-MK-Locale')).toBe('en')
  })

  it('omits X-MK-Locale when no lang is set', () => {
    document.documentElement.lang = ''
    const h = buildApiHeaders({ method: 'GET' })
    expect(h.get('X-MK-Locale')).toBeNull()
  })

  it('does not override an explicit X-MK-Locale header', () => {
    document.documentElement.lang = 'en'
    const h = buildApiHeaders({ headers: { 'X-MK-Locale': 'fr' } })
    expect(h.get('X-MK-Locale')).toBe('fr')
  })
})
