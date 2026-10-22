/**
 * Statistics → Tools result lines, rendered by the real translations: one
 * singular and one plural form per count, in French and English.
 */
import { describe, it, expect, afterEach } from 'vitest'
import i18n from '@/i18n'

const initial = i18n.global.locale.value
const t = (key, n) => i18n.global.t(key, n)

afterEach(() => {
  i18n.global.locale.value = initial
})

describe('Tools tab result texts', () => {
  it.each([
    ['fr', 'stats.playsImported', '1 lecture importée', '12 lectures importées'],
    ['fr', 'stats.duplicatesIgnored', '1 doublon ignoré', '3 doublons ignorés'],
    ['fr', 'stats.playsPurged', '1 lecture supprimée', '42 lectures supprimées'],
    ['en', 'stats.playsImported', '1 play imported', '12 plays imported'],
    ['en', 'stats.duplicatesIgnored', '1 duplicate skipped', '3 duplicates skipped'],
    ['en', 'stats.playsPurged', '1 play deleted', '42 plays deleted'],
  ])('%s %s: singular, then plural', (locale, key, one, many) => {
    i18n.global.locale.value = locale
    expect(t(key, 1)).toBe(one)
    expect(t(key, Number(many.split(' ')[0]))).toBe(many)
  })

  it('joins the two import counts in each language', () => {
    i18n.global.locale.value = 'fr'
    expect(i18n.global.t('stats.importResult', { imported: 'A', skipped: 'B' })).toBe('A, B')
    i18n.global.locale.value = 'en'
    expect(i18n.global.t('stats.importResult', { imported: 'A', skipped: 'B' })).toBe('A, B')
  })
})
