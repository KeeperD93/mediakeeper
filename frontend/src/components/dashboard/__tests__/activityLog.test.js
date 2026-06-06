import { describe, it, expect } from 'vitest'
import { parseActivityLog, parseActivityAlert } from '@/components/dashboard/activityLog'

// Pure parsers: the fake `t` echoes its key (and appends `|<user>` for messages
// carrying a `user` param) so we can assert which translation is selected and
// that the username was extracted — never read from Emby's localized `name`.
const t = (key, params) => (params ? `${key}|${params.user ?? ''}` : key)

describe('parseActivityLog', () => {
  it('maps playback.start to the watching action with media + device (FR)', () => {
    expect(
      parseActivityLog(
        { type: 'playback.start', name: 'Alice est en train de lire Mon Film sur Salon TV' },
        t,
      ),
    ).toEqual({
      user: 'Alice',
      action: 'dashboard.watching',
      media: 'Mon Film',
      rawMediaName: 'Mon Film',
      device: 'Salon TV',
    })
  })

  it('maps playback.stop to the finished action and omits the device', () => {
    const r = parseActivityLog(
      {
        type: 'playback.stop',
        name: "Alice vient d'arrêter la lecture de Ma Série - S2, Ep3 - Titre sur Salon TV",
      },
      t,
    )
    expect(r.action).toBe('dashboard.finished')
    expect(r.media).toBe('Ma Série - S2, Ep3 - Titre')
    expect(r.rawMediaName).toBe('Ma Série')
    expect(r.device).toBe('')
  })

  it('maps user.authenticated to the signedIn action with no media', () => {
    expect(
      parseActivityLog(
        { type: 'user.authenticated', name: "Bob s'est authentifié sur MonServeur" },
        t,
      ),
    ).toEqual({
      user: 'Bob',
      action: 'dashboard.signedIn',
      media: '',
      rawMediaName: '',
      device: '',
    })
  })

  it('parses an English Emby playback entry (action stays locale-independent)', () => {
    const r = parseActivityLog(
      { type: 'playback.start', name: 'Carol is playing My Movie on Living Room' },
      t,
    )
    expect(r.user).toBe('Carol')
    expect(r.action).toBe('dashboard.watching')
    expect(r.media).toBe('My Movie')
    expect(r.device).toBe('Living Room')
  })

  it('keeps the title intact when it itself contains the device separator', () => {
    const r = parseActivityLog(
      {
        type: 'playback.start',
        name: 'Frank est en train de lire Le Pont sur la Rivière sur Chromecast',
      },
      t,
    )
    expect(r.media).toBe('Le Pont sur la Rivière')
    expect(r.device).toBe('Chromecast')
  })

  it('leaves the device empty when the entry has no separator', () => {
    const r = parseActivityLog(
      { type: 'playback.start', name: 'Eve est en train de lire Film Sans Device' },
      t,
    )
    expect(r.media).toBe('Film Sans Device')
    expect(r.device).toBe('')
  })

  it('falls back to the raw label for an unknown type', () => {
    const r = parseActivityLog({ type: 'system.unhandled', name: 'Raw Emby text' }, t)
    expect(r.user).toBe('dashboard.system')
    expect(r.action).toBe('Raw Emby text')
    expect(r.media).toBe('')
  })

  it('keeps the backend-provided user instead of parsing the name', () => {
    const r = parseActivityLog({ type: 'user.authenticated', name: 'irrelevant', user: 'Dave' }, t)
    expect(r.user).toBe('Dave')
    expect(r.action).toBe('dashboard.signedIn')
  })
})

describe('parseActivityAlert', () => {
  it('localizes a failed sign-in and keeps the attempted username (FR)', () => {
    const r = parseActivityAlert(
      {
        type: 'user.authenticationfailed',
        name: 'Tentative de connexion échouée pour mallory sur MonServeur',
      },
      t,
    )
    expect(r).toBe('dashboard.signInFailedFor|mallory')
  })

  it('extracts the username from an English failed-sign-in line', () => {
    const r = parseActivityAlert(
      { type: 'user.authenticationfailed', name: 'Failed sign-in for trudy from Roku' },
      t,
    )
    expect(r).toBe('dashboard.signInFailedFor|trudy')
  })

  it('extracts the username when no trailing separator is present', () => {
    const r = parseActivityAlert(
      { type: 'user.authenticationfailed', name: 'Tentative de connexion échouée pour mallory' },
      t,
    )
    expect(r).toBe('dashboard.signInFailedFor|mallory')
  })

  it('falls back to the generic label when no username can be extracted', () => {
    const r = parseActivityAlert(
      { type: 'user.authenticationfailed', name: 'Authentication failure' },
      t,
    )
    expect(r).toBe('dashboard.signInFailed')
  })

  it('keeps the raw Emby label for unmapped alert types', () => {
    const r = parseActivityAlert({ type: 'plugin.installed', name: 'Plugin X installed' }, t)
    expect(r).toBe('Plugin X installed')
  })
})
