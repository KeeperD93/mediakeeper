/* Pure stats formatters extracted from useStats so they stay unit-testable
   and don't bloat the composable. No reactive / i18n deps — i18n-bound
   formatters (ticksToDuration, timeAgo) remain in useStats. */

export function ticksToTime(t) {
  const s = Math.floor(t / 1e7),
    h = Math.floor(s / 3600),
    m = Math.floor((s % 3600) / 60),
    sec = s % 60
  return `${h}:${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`
}

export function ticksToHours(t) {
  if (!t) return '—'
  const h = Math.floor(t / 1e7 / 3600),
    m = Math.floor(((t / 1e7) % 3600) / 60)
  return h > 0 ? `${h.toLocaleString(undefined)}h ${m}min` : `${m}min`
}

export function fmtSize(b) {
  if (!b) return '—'
  if (b >= 1099511627776) return `${(b / 1099511627776).toFixed(2)} TB`
  if (b >= 1073741824) return `${(b / 1073741824).toFixed(2)} GB`
  return `${(b / 1048576).toFixed(1)} MB`
}

export function langLabel(l) {
  const m = {
    fr: 'French',
    en: 'English',
    de: 'German',
    es: 'Spanish',
    it: 'Italian',
    ja: 'Japanese',
    ko: 'Korean',
    pt: 'Portuguese',
    ru: 'Russian',
    zh: 'Chinese',
    ar: 'Arabic',
    nl: 'Dutch',
    pl: 'Polish',
    sv: 'Swedish',
    da: 'Danish',
    fi: 'Finnish',
    no: 'Norwegian',
    tr: 'Turkish',
    th: 'Thai',
    hi: 'Hindi',
    fre: 'French',
    fra: 'French',
    eng: 'English',
    ger: 'German',
    deu: 'German',
    spa: 'Spanish',
    ita: 'Italian',
    jpn: 'Japanese',
    kor: 'Korean',
    por: 'Portuguese',
    rus: 'Russian',
    chi: 'Chinese',
    zho: 'Chinese',
    ara: 'Arabic',
    dut: 'Dutch',
    nld: 'Dutch',
    pol: 'Polish',
    swe: 'Swedish',
    dan: 'Danish',
    fin: 'Finnish',
    nor: 'Norwegian',
    tur: 'Turkish',
    tha: 'Thai',
    und: 'Unknown',
  }
  return m[(l || '').toLowerCase()] || (l || '').toUpperCase() || ''
}

export function langShort(l) {
  const m = {
    fr: 'FR',
    en: 'EN',
    de: 'DE',
    es: 'ES',
    it: 'IT',
    ja: 'JA',
    fre: 'FR',
    eng: 'EN',
    ger: 'DE',
    spa: 'ES',
    jpn: 'JA',
    fra: 'FR',
    deu: 'DE',
    ita: 'IT',
    kor: 'KO',
    por: 'PT',
    rus: 'RU',
  }
  return m[(l || '').toLowerCase()] || ''
}

export function parseTicks(str) {
  if (!str) return 0
  const p = str.split(':').map(Number)
  return p.length === 3 ? (p[0] * 3600 + p[1] * 60 + p[2]) * 1e7 : 0
}
