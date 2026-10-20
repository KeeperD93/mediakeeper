/**
 * Every status a poster ribbon can show has its colour token and a label in
 * both languages, so no status renders an empty or untranslated ribbon.
 */
import { describe, it, expect } from 'vitest'
import { POSTER_STATUS, POSTER_STATUS_RIBBON } from '@/constants/portal'
import fr from '@/locales/fr.json'
import en from '@/locales/en.json'

const message = (messages, key) => key.split('.').reduce((node, part) => node?.[part], messages)

describe('POSTER_STATUS_RIBBON', () => {
  it.each(Object.values(POSTER_STATUS))('gives "%s" a colour and a label', status => {
    const { color, labelKey } = POSTER_STATUS_RIBBON[status]

    expect(color).toMatch(/^var\(--portal-color-[a-z-]+\)$/)
    expect(message(fr, labelKey)).toEqual(expect.any(String))
    expect(message(en, labelKey)).toEqual(expect.any(String))
  })
})
