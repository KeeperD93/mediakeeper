/**
 * The sign-in page's messages, through the real locale files: the texts below
 * were validated as written, and a wrong placeholder would only show on screen.
 */
import { describe, it, expect, vi, afterEach } from 'vitest'

vi.mock('@/i18n', async () => {
  const { createI18n } = await import('vue-i18n')
  const fr = (await import('@/locales/fr.json')).default
  return { default: createI18n({ legacy: false, locale: 'fr', messages: { fr } }) }
})

import { signInErrorMessage } from '@/composables/signInErrors'
import { useAuth } from '@/composables/useAuth'
import { useToast } from '@/composables/useToast'

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

  it('says when the media server cannot judge the password', () => {
    expect(message('media_server_unreachable')).toBe(
      'Le serveur média ne répond pas. Réessayez dans quelques minutes.',
    )
    expect(message('media_server_not_configured')).toBe(
      "Connexion des membres indisponible : aucun serveur média n'est configuré.",
    )
  })

  it('says an account is no longer active, on this page only', () => {
    expect(message('account_disabled')).toBe(
      "Ce compte n'est plus actif. Contactez l'administrateur.",
    )
  })

  it('ignores a wait on any other refusal', () => {
    expect(message('invalid_credentials', 42)).toBe('Identifiants incorrects.')
  })

  it('stays silent when the shared toast already spoke', () => {
    expect(message('rate_limited_notified', null)).toBe('')
  })
})

describe('a refusal from the server to the sign-in page', () => {
  const answered = (body, headers, status = 429) =>
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => new Response(JSON.stringify(body), { status, headers })),
    )
  const signIn = () =>
    useAuth()
      .login('someone', 'not-a-real-password')
      .catch(failure => failure)

  afterEach(() => {
    vi.unstubAllGlobals()
    const { toasts, removeToast } = useToast()
    toasts.value.forEach(toast => removeToast(toast.id))
  })

  it('reaches the page with its wait, and no toast', async () => {
    answered({ detail: 'login_rate_limited' }, { 'Retry-After': '42' })

    expect(signInErrorMessage(await signIn())).toBe(
      'Trop de tentatives en peu de temps. Réessayez dans 42 s.',
    )
    expect(useToast().toasts.value).toEqual([])
  })

  it('names an unreachable media server, not a startup', async () => {
    answered({ detail: 'media_server_unreachable' }, {}, 503)

    expect(signInErrorMessage(await signIn())).toBe(
      'Le serveur média ne répond pas. Réessayez dans quelques minutes.',
    )
  })

  it('names an inactive account', async () => {
    answered({ detail: 'account_disabled' }, {}, 403)

    expect(signInErrorMessage(await signIn())).toBe(
      "Ce compte n'est plus actif. Contactez l'administrateur.",
    )
  })

  it('without a reason, stays the shared toast and leaves the page silent', async () => {
    answered({ error: 'Rate limit exceeded' })

    expect(signInErrorMessage(await signIn())).toBe('')
    expect(useToast().toasts.value.map(toast => toast.message)).toEqual([
      "Trop d'actions en peu de temps. Patientez un instant.",
    ])
  })
})
