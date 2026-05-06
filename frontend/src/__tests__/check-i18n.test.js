import { describe, it, expect } from 'vitest'
import {
  flattenLocale,
  extractPlaceholders,
  validateLocales,
  extractRouteI18nKeys,
} from '../../scripts/check-i18n.mjs'

describe('flattenLocale', () => {
  it('flattens nested objects with dot notation', () => {
    const flat = flattenLocale({ a: { b: 'x', c: { d: 'y' } }, e: 'z' })
    expect([...flat.entries()]).toEqual([
      ['a.b', 'x'],
      ['a.c.d', 'y'],
      ['e', 'z'],
    ])
  })
})

describe('extractPlaceholders', () => {
  it('extracts {name} style placeholders', () => {
    expect([...extractPlaceholders('hello {name}, {count} items')]).toEqual(['{name}', '{count}'])
  })

  it('returns empty set for plain strings or non-strings', () => {
    expect(extractPlaceholders('plain text').size).toBe(0)
    expect(extractPlaceholders(42).size).toBe(0)
  })
})

describe('extractRouteI18nKeys', () => {
  it('finds titleKey/subtitleKey route definitions', () => {
    const source = `
      { path: '/a', name: 'a', meta: { titleKey: 'routes.a.title', subtitleKey: 'routes.a.sub' } },
      { path: '/b', name: 'b', meta: { titleKey: "routes.b.title" } },
    `
    expect(extractRouteI18nKeys(source)).toEqual([
      'routes.a.sub',
      'routes.a.title',
      'routes.b.title',
    ])
  })
})

describe('validateLocales', () => {
  it('passes on symmetric locales with matching placeholders', () => {
    const fr = { greet: 'Bonjour {name}', plays: '{n} lecture | {n} lectures' }
    const en = { greet: 'Hello {name}', plays: '{n} play | {n} plays' }
    expect(validateLocales({ locales: { fr, en } })).toEqual([])
  })

  it('flags missing keys in non-reference locale', () => {
    const fr = { a: 'A', b: 'B' }
    const en = { a: 'A' }
    const failures = validateLocales({ locales: { fr, en } })
    expect(failures).toContain('[en] missing keys vs fr: b')
  })

  it('flags extra keys in non-reference locale', () => {
    const fr = { a: 'A' }
    const en = { a: 'A', extra: 'X' }
    const failures = validateLocales({ locales: { fr, en } })
    expect(failures).toContain('[en] extra keys vs fr: extra')
  })

  it('flags placeholder mismatches', () => {
    const fr = { msg: 'Bonjour {name}, vous avez {count} messages' }
    const en = { msg: 'Hello {name}' }
    const failures = validateLocales({ locales: { fr, en } })
    expect(failures.some((f) => f.includes('placeholder mismatch at "msg"'))).toBe(true)
    expect(failures.some((f) => f.includes('missing {count}'))).toBe(true)
  })

  it('flags empty values', () => {
    const fr = { a: 'A', empty: '' }
    const en = { a: 'A', empty: '' }
    const failures = validateLocales({ locales: { fr, en } })
    expect(failures).toContain('[fr] empty value at "empty"')
    expect(failures).toContain('[en] empty value at "empty"')
  })

  it('flags non-string values', () => {
    const fr = { count: 42 }
    const en = { count: 42 }
    const failures = validateLocales({ locales: { fr, en } })
    expect(failures.some((f) => f.includes('non-string value at "count"'))).toBe(true)
  })

  it('flags missing route keys in any locale', () => {
    const fr = { 'routes.a.title': 'Accueil' }
    const en = { 'routes.a.title': 'Home' }
    const failures = validateLocales({
      locales: { fr, en },
      routeKeys: ['routes.a.title', 'routes.b.title'],
    })
    expect(failures).toContain('[fr] route key missing: routes.b.title')
    expect(failures).toContain('[en] route key missing: routes.b.title')
  })
})
