import {
  NAMING_PATTERNS,
  GENRE_CAT_MAP,
  newFileThresholdMs,
  releaseTags,
} from './mediaManagerState'
import { DIFF_TYPE } from '@/constants/mediaManager'

export function sanitize(n) {
  return n
    .replace(/\s*:\s*/g, ' - ')
    .replace(/,/g, '')
    .replace(/[/\\]/g, ' ')
    .replace(/[<>"|?*]/g, '')
    .replace(/\s{2,}/g, ' ')
    .trim()
}

let _tagsRe = null
let _tagsKey = ''
function _buildTagsRegex() {
  const tags = (releaseTags.value || []).filter(Boolean)
  const key = tags.join('\u0001').toLowerCase()
  if (key === _tagsKey) return _tagsRe
  _tagsKey = key
  if (!tags.length) {
    _tagsRe = null
    return null
  }
  // Tags may be plain words OR small regex fragments (e.g. "Customs?",
  // "AAC\d?(?:\.\d)?"). Trust the backend default list and admin input —
  // an invalid regex fragment falls back to a literal-escape compile.
  let body
  try {
    new RegExp(`\\b(?:${tags.join('|')})\\b`, 'gi')
    body = tags.join('|')
  } catch {
    body = tags.map(t => t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')
  }
  _tagsRe = new RegExp(`\\b(?:${body})\\b`, 'gi')
  return _tagsRe
}

export function cleanName(name) {
  let n = name.replace(/\.[^.]+$/, '')
  n = n.replace(/\[[^\]]*\]/g, '')
  n = n.replace(/\([^)]*\)/g, '')
  n = n.replace(/[._\s-]*S\d{2}(E\d{2})?.*/i, '')
  n = n.replace(/[._\s-]*(seasons?|seasons?)\b.*/i, '')
  n = n.replace(/[._\s-]*(episodes?|episodes?|ep)\s*\d*.*/i, '')
  n = n.replace(/[._\s-]*\(?(19|20)\d{2}\)?.*/i, '')
  const tagsRe = _buildTagsRegex()
  if (tagsRe) n = n.replace(tagsRe, '')
  n = n.replace(/\b\d{1}\b/g, '')
  n = n.replace(/[-_.]+/g, ' ').trim()
  return n
}

export function getGenreCategory(genreIds) {
  if (!genreIds?.length) return null
  for (const gid of [16, 99, 10402]) {
    if (genreIds.includes(gid)) return GENRE_CAT_MAP[gid]
  }
  return null
}

export function computeQualityScore(name) {
  let score = 100
  const n = name.replace(/\.[^.]+$/, '')
  if (!NAMING_PATTERNS.resolution.test(name)) score -= 20
  if (!NAMING_PATTERNS.year.test(name) && !NAMING_PATTERNS.episode.test(name)) score -= 15
  if (/[-_.]{3,}/.test(n)) score -= 10
  if (/\s{2,}/.test(n)) score -= 10
  if (/_{2,}/.test(n)) score -= 10
  if ((n.match(/\./g) || []).length > 3) score -= 15
  if (name.length > 180) score -= 10
  if (!/\b(x264|x265|H\.?264|H\.?265|HEVC|AVC|VP9|AV1)\b/i.test(name)) score -= 5
  if (!/\b(DTS|Atmos|TrueHD|EAC3|AC3|AAC|FLAC|MP3)\b/i.test(name)) score -= 5
  if (/^[A-Z]/.test(n)) score += 5
  return Math.max(0, Math.min(100, score))
}

export function getQualityColor(score) {
  if (score >= 80) return 'var(--color-success)'
  if (score >= 55) return 'var(--color-warning)'
  return 'var(--color-error)'
}

export function detectSeasonNum(name) {
  for (const re of [/^(?:saison|season)\s*(\d{1,2})$/i, /^[Ss]\s*(\d{1,2})$/, /^(\d{1,2})$/]) {
    const m = name.match(re)
    if (m) return parseInt(m[1])
  }
  for (const re of [/(?:saison|season)\s*(\d{1,2})/i, /\bs(\d{1,2})\b/i]) {
    const m = name.match(re)
    if (m) return parseInt(m[1])
  }
  return null
}

export function isFileNew(f) {
  if (!f?.mtime) return false
  return Date.now() - f.mtime * 1000 < newFileThresholdMs
}

export function _levenshtein(a, b) {
  const m = a.length,
    n = b.length
  const dp = Array.from({ length: m + 1 }, (_, i) =>
    Array.from({ length: n + 1 }, (_, j) => (i === 0 ? j : j === 0 ? i : 0)),
  )
  for (let i = 1; i <= m; i++)
    for (let j = 1; j <= n; j++)
      dp[i][j] =
        a[i - 1] === b[j - 1]
          ? dp[i - 1][j - 1]
          : 1 + Math.min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1])
  return dp[m][n]
}

export function computeDiff(oldName, newName) {
  const o = oldName.replace(/\.[^.]+$/, '')
  const n = newName.replace(/\.[^.]+$/, '')
  if (o === n) return [{ type: 'same', text: o }]
  const oTokens = o.split(/(?=[\s\-_.])|(?<=[\s\-_.])/g)
  const nTokens = n.split(/(?=[\s\-_.])|(?<=[\s\-_.])/g)
  const result = []
  let oi = 0,
    ni = 0
  while (oi < oTokens.length || ni < nTokens.length) {
    if (oi < oTokens.length && ni < nTokens.length && oTokens[oi] === nTokens[ni]) {
      result.push({ type: 'same', text: oTokens[oi] })
      oi++
      ni++
    } else if (ni < nTokens.length) {
      result.push({ type: DIFF_TYPE.ADD, text: nTokens[ni] })
      ni++
    } else {
      result.push({ type: DIFF_TYPE.DEL, text: oTokens[oi] })
      oi++
    }
  }
  return result
}

export function _parseFileName(name) {
  const n = name.replace(/\.[^.]+$/, '')
  const result = {}

  const resM = n.match(/\b(480p|576p|720p|1080p|1080i|2160p|4K|UHD|2K|4k)\b/i)
  if (resM) result.resolution = resM[1].toUpperCase()

  const srcM = n.match(
    /\b(BluRay|BDRip|BRRip|WEBRip|WEB-DL|WEBDL|WEB|HDTV|DVDRip|DVD|HDDVD|AMZN|NF|DSNP|ATVP|HMAX|PCOK|SHO|iT)\b/i,
  )
  if (srcM) result.source = srcM[1]

  const vcodM = n.match(/\b(x264|x265|H\.?264|H\.?265|HEVC|AVC|VP9|AV1|XVID|MPEG2|VC-1|MPEG-2)\b/i)
  if (vcodM)
    result.codec_video = vcodM[1].toUpperCase().replace('H264', 'H.264').replace('H265', 'H.265')

  const acodM = n.match(
    /\b(DTS(?:-HD|-X|-MA)?|Atmos|TrueHD|EAC3|AC3|AAC|MP3|FLAC|DDP|DD\+?5\.1|DDP\d|PCM|OPUS)\b/i,
  )
  if (acodM) result.codec_audio = acodM[1].toUpperCase()

  const hdrM = n.match(/\b(HDR10\+?|HDR|DV|Dolby\.?Vision|HLG|SDR)\b/i)
  if (hdrM) result.hdr = hdrM[1]

  const bitM = n.match(/\b(10bit|8bit|10-bit|8-bit|Hi10P)\b/i)
  if (bitM) result.bit_depth = bitM[1]

  const langTags = []
  const langPatterns = [
    { re: /\bMULTI\b/i, v: 'MULTI (FR+OV)' },
    { re: /\bVOSTFR\b/i, v: 'VOSTFR (Original with FR subs)' },
    { re: /\bVOSTA\b/i, v: 'VOSTA (Original with EN subs)' },
    { re: /\bVFF\b/i, v: 'VFF (Full French)' },
    { re: /\bVFI\b/i, v: 'VFI (Full French intl.)' },
    { re: /\bVF\b/i, v: 'VF (French dub)' },
    { re: /\bVO\b/i, v: 'VO (Original Version)' },
    { re: /\bFRENCH\b/i, v: 'FRENCH' },
    { re: /\bENGLiSH\b/i, v: 'ENGLISH' },
    { re: /\bDUAL\.?AUDIO\b/i, v: 'Dual Audio' },
    { re: /\bTRiLiNGUAL\b/i, v: 'Trilingual' },
  ]
  for (const { re, v } of langPatterns) {
    if (re.test(n)) langTags.push(v)
  }
  if (langTags.length) result.langues = langTags.join(', ')

  const subTags = []
  if (/\bVOSTFR\b/i.test(n)) subTags.push('FR')
  if (/\bVOSTA\b/i.test(n)) subTags.push('EN')
  if (/\bSUBS?\b/i.test(n)) subTags.push('included')
  if (/\bNOSUBS?\b/i.test(n)) subTags.push('none')
  if (subTags.length) result.sous_titres = subTags.join(', ')

  const yearM = n.match(/\b((?:19|20)\d{2})\b/)
  if (yearM) result.annee = yearM[1]

  const seM = n.match(/[Ss](\d{1,2})[Ee](\d{1,2})/)
  if (seM) result.episode = `Season ${seM[1]} · Episode ${seM[2]}`

  const edM = n.match(
    /\b(Extended|Director'?s\.?Cut|Unrated|Theatrical|Remastered|Anniversary|Ultimate|Redux|Special\.Edition)\b/i,
  )
  if (edM) result.edition = edM[1].replace(/\./g, ' ')

  const qualM = n.match(/\b(PROPER|REPACK|REAL\.PROPER|INTERNAL|READNFO)\b/i)
  if (qualM) result.qualite_note = qualM[1]

  const teamM = n.match(/[-[]([A-Za-z0-9_]{2,15})(?:\])?$/)
  if (teamM && !/^\d+$/.test(teamM[1])) result.team = teamM[1]

  const fpsM = n.match(/\b(23\.976|24|25|29\.97|30|48|50|59\.94|60)\s*fps\b/i)
  if (fpsM) result.framerate = fpsM[1] + ' fps'

  return Object.keys(result).length ? result : null
}
