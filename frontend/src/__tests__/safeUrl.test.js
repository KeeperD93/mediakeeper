import { describe, it, expect } from 'vitest'
import { safeHref, safeIframeSrc } from '@/utils/safeUrl'

describe('safeHref', () => {
  it('accepts https absolute URLs', () => {
    expect(safeHref('https://example.com/path?q=1#x')).toBe('https://example.com/path?q=1#x')
  })

  it('accepts http absolute URLs', () => {
    expect(safeHref('http://example.com')).toBe('http://example.com')
  })

  it('accepts mailto URIs', () => {
    expect(safeHref('mailto:user@example.com')).toBe('mailto:user@example.com')
  })

  it('accepts relative paths starting with /', () => {
    expect(safeHref('/login')).toBe('/login')
    expect(safeHref('/api/portal/avatars/x.png')).toBe('/api/portal/avatars/x.png')
  })

  it('accepts relative paths starting with ./ or ../', () => {
    expect(safeHref('./foo')).toBe('./foo')
    expect(safeHref('../bar')).toBe('../bar')
  })

  it('accepts query-only and fragment-only URLs', () => {
    expect(safeHref('?q=1')).toBe('?q=1')
    expect(safeHref('#anchor')).toBe('#anchor')
  })

  it('blocks javascript: scheme', () => {
    expect(safeHref('javascript:alert(1)')).toBeNull()
    expect(safeHref('JaVaScRiPt:alert(1)')).toBeNull()
  })

  it('blocks javascript: scheme even with leading whitespace and tabs', () => {
    expect(safeHref('  javascript:alert(1)')).toBeNull()
    expect(safeHref('\tjavascript:alert(1)')).toBeNull()
    expect(safeHref('java\nscript:alert(1)')).toBeNull()
    expect(safeHref('java\tscript:alert(1)')).toBeNull()
  })

  it('blocks data: scheme', () => {
    expect(safeHref('data:text/html,<script>alert(1)</script>')).toBeNull()
  })

  it('blocks vbscript: scheme', () => {
    expect(safeHref('vbscript:msgbox(1)')).toBeNull()
  })

  it('blocks file: scheme', () => {
    expect(safeHref('file:///etc/passwd')).toBeNull()
  })

  it('blocks about: scheme', () => {
    expect(safeHref('about:blank')).toBeNull()
  })

  it('blocks unknown schemes', () => {
    expect(safeHref('chrome://settings')).toBeNull()
    expect(safeHref('ftp://example.com')).toBeNull()
    expect(safeHref('ws://example.com')).toBeNull()
  })

  it('rejects empty / null / undefined inputs', () => {
    expect(safeHref('')).toBeNull()
    expect(safeHref(null)).toBeNull()
    expect(safeHref(undefined)).toBeNull()
    expect(safeHref('   ')).toBeNull()
  })

  it('rejects bare relative tokens without an explicit prefix', () => {
    expect(safeHref('foo')).toBeNull()
    expect(safeHref('foo/bar')).toBeNull()
  })
})

describe('safeIframeSrc', () => {
  it('accepts https absolute URLs', () => {
    expect(safeIframeSrc('https://www.youtube-nocookie.com/embed/abc')).toBe(
      'https://www.youtube-nocookie.com/embed/abc',
    )
  })

  it('rejects http (mixed-content surface)', () => {
    expect(safeIframeSrc('http://example.com')).toBeNull()
  })

  it('rejects mailto', () => {
    expect(safeIframeSrc('mailto:x@y')).toBeNull()
  })

  it('rejects relative paths', () => {
    expect(safeIframeSrc('/embed/x')).toBeNull()
    expect(safeIframeSrc('./foo')).toBeNull()
  })

  it('blocks javascript:, data:, vbscript:, file:, about: schemes', () => {
    expect(safeIframeSrc('javascript:alert(1)')).toBeNull()
    expect(safeIframeSrc('data:text/html,x')).toBeNull()
    expect(safeIframeSrc('vbscript:msgbox')).toBeNull()
    expect(safeIframeSrc('file:///etc/passwd')).toBeNull()
    expect(safeIframeSrc('about:blank')).toBeNull()
  })

  it('rejects empty / null / undefined inputs', () => {
    expect(safeIframeSrc('')).toBeNull()
    expect(safeIframeSrc(null)).toBeNull()
    expect(safeIframeSrc(undefined)).toBeNull()
  })
})
