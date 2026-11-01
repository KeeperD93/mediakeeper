/**
 * The sign-in page's messages, through the real locale files: the texts below
 * were validated as written, and a wrong placeholder would only show on screen.
 */
import { describe, it, expect, vi } from 'vitest'

vi.mock('@/i18n', async () => {
  const { createI18n } = await import('vue-i18n')
  const fr = (await import('@/locales/fr.json')).default
  return { default: createI18n({ legacy: false, locale: 'fr', messages: { fr } }) }
})

import { signInErrorMessage } from '@/composables/signInErrors'

const message = (code, retryAfter) => signInErrorMessage({ message: code, retryAfter })

describe('signInErrorMessage', () => {
  it('gives the wait of the per-minute limit, in seconds', () => {
    expect(message('login_rate_limited', 42)).toBe(
      'Trop de tentatives en peu de temps. Réessayez dans 42 s.',
    )
  })

  it('gives the wait of a block, rounded up to the minute', () => {
    expect(message('login_blocked', 540)).toBe(
      'Connexion bloquée pour le moment. Réessayez dans 9 min.',
    )
    expect(message('login_blocked', 61)).toBe(
      'Connexion bloquée pour le moment. Réessayez dans 2 min.',
    )
    expect(message('login_blocked', 60)).toBe(
      'Connexion bloquée pour le moment. Réessayez dans 1 min.',
    )
  })

  it('keeps seconds just under the minute', () => {
    expect(message('login_rate_limited', 59)).toBe(
      'Trop de tentatives en peu de temps. Réessayez dans 59 s.',
    )
  })

  it('points to the administrator for a block with no wait', () => {
    const expected =
      "Connexion bloquée pour le moment. Réessayez plus tard ou contactez l'administrateur."

    expect(message('login_blocked', null)).toBe(expected)
    expect(message('login_blocked', undefined)).toBe(expected)
  })

  it('does not count down a wait of an hour or more', () => {
    expect(message('login_blocked', 3600)).toBe(
      "Connexion bloquée pour le moment. Réessayez plus tard ou contactez l'administrateur.",
    )
  })

  it('says to wait a moment when the limit gives no time', () => {
    expect(message('login_rate_limited', null)).toBe(
      'Trop de tentatives en peu de temps. Réessayez dans un instant.',
    )
    expect(message('login_rate_limited', 0)).toBe(
      'Trop de tentatives en peu de temps. Réessayez dans un instant.',
    )
  })

  it('ignores a wait on any other refusal', () => {
    expect(message('invalid_credentials', 42)).toBe('Identifiants incorrects.')
  })

  it('stays silent when the shared toast already spoke', () => {
    expect(message('rate_limited_notified', null)).toBe('')
  })
})
