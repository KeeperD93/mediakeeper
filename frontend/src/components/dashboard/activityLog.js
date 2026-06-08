// Pure Emby activity-feed parsers (no Vue/i18n deps — `t` is passed in) so they
// stay unit-testable. Consumed by useActivityTimeline.js.

// Emby tags each entry with a machine-readable `type`, so the displayed verb
// comes from our translations, not the localized `entry.name`. The name is
// parsed only to recover username/media/device — FR + EN for either Emby locale.
const PLAYBACK_TYPES = new Set(['playback.start', 'playback.stop'])
const NAME_VERBS = {
  'playback.start': [
    ' est en train de lire ',
    ' a démarré la lecture de ',
    ' is playing ',
    ' started playing ',
  ],
  'playback.stop': [
    " vient d'arrêter la lecture de ",
    " vient d'arrêter ",
    ' has finished playing ',
    ' stopped playing ',
    ' finished playing ',
  ],
  'user.authenticated': [
    " s'est authentifié",
    ' has authenticated',
    ' authenticated',
    ' signed in',
  ],
}
const DEVICE_SEPARATORS = [' sur ', ' on ']

// Plugin-update entries (`plugins.pluginupdated`) embed the whole sentence in
// the localized name: "<plugin> <verb> <version> sur/on <server>". Parse the
// FR + EN variants to recover plugin + version so the row renders in the
// viewer's language. The server name is dropped (always this instance).
const PLUGIN_UPDATE_VERBS = [' est mis à jour vers ', ' has been updated to ', ' updated to ']

function parsePluginUpdate(name) {
  for (const verb of PLUGIN_UPDATE_VERBS) {
    const idx = name.indexOf(verb)
    if (idx === -1) continue
    const plugin = name.slice(0, idx).trim()
    let rest = name.slice(idx + verb.length)
    for (const sep of DEVICE_SEPARATORS) {
      const i = rest.lastIndexOf(sep)
      if (i !== -1) {
        rest = rest.slice(0, i)
        break
      }
    }
    const version = rest.trim()
    if (plugin && version) return { plugin, version }
  }
  return null
}

function logActionLabel(type, t) {
  if (type === 'playback.start') return t('dashboard.watching')
  if (type === 'playback.stop') return t('dashboard.finished')
  if (type === 'user.authenticated') return t('dashboard.signedIn')
  return ''
}

function extractBaseName(mediaStr) {
  return mediaStr
    .replace(/ - S\d+.*$/i, '')
    .replace(/ S\d+E\d+.*$/i, '')
    .replace(/ - Saison.*$/i, '')
    .replace(/ saison.*$/i, '')
    .trim()
}

// Turn one Emby activity-log entry into a display row.
export function parseActivityLog(log, t) {
  const name = log.name || ''
  const type = log.type || ''
  const action = logActionLabel(type, t)

  let user = log.user || ''
  let remainder = ''
  for (const verb of NAME_VERBS[type] || []) {
    const idx = name.indexOf(verb)
    if (idx === -1) continue
    if (!user) user = name.slice(0, idx).trim()
    remainder = name.slice(idx + verb.length)
    break
  }
  if (!user) user = t('dashboard.system')

  if (type === 'plugins.pluginupdated') {
    const pu = parsePluginUpdate(name)
    if (pu) {
      return {
        user,
        action: t('dashboard.pluginUpdated', pu),
        media: '',
        rawMediaName: '',
        device: '',
      }
    }
  }

  if (PLAYBACK_TYPES.has(type)) {
    let media = remainder
    let device = ''
    for (const sep of DEVICE_SEPARATORS) {
      const i = remainder.lastIndexOf(sep)
      if (i === -1) continue
      media = remainder.slice(0, i)
      device = remainder.slice(i + sep.length)
      break
    }
    media = media.trim()
    return {
      user,
      action,
      media,
      rawMediaName: extractBaseName(media),
      // Match prior behavior: device shown on start, omitted on stop.
      device: type === 'playback.start' ? device.trim() : '',
    }
  }

  if (action) return { user, action, media: '', rawMediaName: '', device: '' }

  // Unknown / unparsed type → raw Emby label fallback (e.g. plugin
  // install/uninstall, system updates — not yet machine-mapped).
  return { user, action: name.slice(0, 80), media: '', rawMediaName: '', device: '' }
}

// Pull the attempted username out of a localized failed-sign-in line
// ("… pour <user> sur …" / "… for <user> from …").
function attemptedUser(name) {
  for (const lead of [' pour ', ' for ']) {
    const i = name.indexOf(lead)
    if (i === -1) continue
    let rest = name.slice(i + lead.length)
    for (const tail of [' sur ', ' from ', ' on ']) {
      const j = rest.indexOf(tail)
      if (j === -1) continue
      rest = rest.slice(0, j)
      break
    }
    return rest.trim()
  }
  return ''
}

// Build the display label for an Emby alert entry (Error/Warning severity).
export function parseActivityAlert(alert, t) {
  if (alert.type === 'user.authenticationfailed') {
    const user = attemptedUser(alert.name || '')
    return user ? t('dashboard.signInFailedFor', { user }) : t('dashboard.signInFailed')
  }
  // Other alert types are not machine-mapped yet → keep Emby's raw label.
  return alert.name || ''
}
