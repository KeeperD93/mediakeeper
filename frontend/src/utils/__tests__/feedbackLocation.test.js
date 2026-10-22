/**
 * Report location of an admin page: the page and its tab, the first tab when
 * the address names none (as the page itself does), nothing outside the list.
 */
import { describe, it, expect } from 'vitest'
import { locationFromRoute } from '@/utils/feedbackLocation'

const NONE = { pageRoute: '', tabId: '' }

describe('locationFromRoute', () => {
  it('keeps a known tab', () => {
    expect(locationFromRoute('stats', 'users')).toEqual({ pageRoute: 'stats', tabId: 'users' })
  })

  it('falls back to the first tab when the tab is missing or unknown', () => {
    expect(locationFromRoute('stats', undefined).tabId).toBe('general')
    expect(locationFromRoute('stats', 'unknown').tabId).toBe('general')
    expect(locationFromRoute('stats', ['users', 'tools']).tabId).toBe('general')
  })

  it('gives no tab to a page without tabs', () => {
    expect(locationFromRoute('media-manager', 'users')).toEqual({
      pageRoute: 'media-manager',
      tabId: '',
    })
  })

  it('maps the moderation page, not the hidden Traceur module', () => {
    expect(locationFromRoute('feedback', undefined)).toEqual({ pageRoute: 'feedback', tabId: '' })
    expect(locationFromRoute('tracker', undefined)).toEqual(NONE)
  })

  it('gives nothing for a page outside the list', () => {
    expect(locationFromRoute('portal-home', 'users')).toEqual(NONE)
  })
})
