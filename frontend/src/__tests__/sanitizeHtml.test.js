/**
 * sanitizeHtml: the one scrub every server HTML goes through before v-html.
 */
import { describe, it, expect } from 'vitest'

import { sanitizeHtml } from '@/utils/sanitizeHtml'

describe('sanitizeHtml', () => {
  it('returns an empty string for missing or empty input', () => {
    for (const empty of [undefined, null, '']) expect(sanitizeHtml(empty)).toBe('')
  })

  it('keeps ordinary rich text unchanged', () => {
    const html =
      '<h2>Test title</h2><p><strong>Alice</strong> <em>and</em> <a href="https://example.com/">a link</a></p><ul><li>one</li></ul>'
    expect(sanitizeHtml(html)).toBe(html)
  })

  it('removes scripts, event handlers and javascript: links', () => {
    const html =
      '<p onclick="alert(1)">Hi</p><script>alert(1)</script><a href="javascript:alert(1)">x</a><img src="x" onerror="alert(1)">'
    expect(sanitizeHtml(html)).toBe('<p>Hi</p><a>x</a><img src="x">')
  })

  it('reads a non-string value as text', () => {
    expect(sanitizeHtml(12345)).toBe('12345')
  })

  it('does not throw on an object whose toString is not a function', () => {
    expect(sanitizeHtml({ toString: 'x' })).toBe('[object Object]')
  })
})
