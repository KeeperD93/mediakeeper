/* Locale-aware formatting of the machine-code media metadata returned by
 * /api/media/metadata (size_bytes, duration_seconds, *_bitrate_bps,
 * channels, language_code, hdr_type). Keeps MMFileMetaModal.vue declarative
 * and lets every value render in the viewer's language (i18n). */

const BYTE_UNITS = ['byte', 'kilobyte', 'megabyte', 'gigabyte', 'terabyte']

// HDR slugs → display. Brand names, identical in every locale, so a plain
// map rather than i18n keys.
const HDR_LABELS = {
  dolby_vision: 'Dolby Vision',
  hdr10_plus: 'HDR10+',
  hdr10: 'HDR10',
  hlg: 'HLG',
}

export function formatBytes(bytes, locale) {
  if (!bytes) return ''
  let value = bytes
  let unit = 0
  while (value >= 1024 && unit < BYTE_UNITS.length - 1) {
    value /= 1024
    unit += 1
  }
  return new Intl.NumberFormat(locale, {
    style: 'unit',
    unit: BYTE_UNITS[unit],
    unitDisplay: 'short',
    maximumFractionDigits: unit === 0 ? 0 : 1,
  }).format(value)
}

export function formatDuration(seconds) {
  if (!seconds) return ''
  const total = Math.floor(seconds)
  const h = Math.floor(total / 3600)
  const m = Math.floor((total % 3600) / 60)
  const s = total % 60
  const pad = n => String(n).padStart(2, '0')
  return h ? `${h}h ${pad(m)}m ${pad(s)}s` : `${m}m ${pad(s)}s`
}

export function formatBitrate(bps, locale) {
  if (!bps) return ''
  // floor (not round) to match the server's historical ``bps // 1000``.
  return `${new Intl.NumberFormat(locale).format(Math.floor(bps / 1000))} kbps`
}

export function hdrLabel(code) {
  return HDR_LABELS[code] || code || ''
}

export function channelsLabel(channels, t) {
  if (!channels) return ''
  if (channels === 1) return t('mediaManager.channels.mono')
  if (channels === 2) return t('mediaManager.channels.stereo')
  if (channels === 6) return '5.1'
  if (channels === 8) return '7.1'
  return t('mediaManager.channels.count', { n: channels })
}

export function languageLabel(code, t) {
  if (!code) return ''
  const key = `mediaManager.languages.${code}`
  const label = t(key)
  // Unknown ISO code (no i18n entry): vue-i18n echoes the key back — fall
  // back to the upper-cased raw code (e.g. "BRE") rather than the dotted path.
  return label === key ? code.toUpperCase() : label
}
