/* Pure helpers for the Duplicates screen — scoring, formatting and the
   rule-matching engine. Kept free of reactive state so they stay trivially
   testable; the reactive orchestration lives in composables/useDuplicates.js. */
import { localizedDate } from '@/utils/datetime'

export function doubKey(item) {
  return `${item.id}_${item.sources.length}`
}

export function srcScore(src) {
  let s = 0
  const h = src.height || 0
  if (h >= 2100) s += 40
  else if (h >= 1000) s += 30
  else if (h >= 700) s += 20
  else s += 5
  const codec = (src.codec || '').toUpperCase()
  if (codec.includes('HEVC') || codec.includes('H265') || codec.includes('X265')) s += 25
  else if (codec.includes('AV1')) s += 30
  else if (codec.includes('H264') || codec.includes('AVC') || codec.includes('X264')) s += 15
  else s += 5
  const mb = (src.size_bytes || 0) / 1048576
  if (mb > 5000) s += 15
  else if (mb > 2000) s += 12
  else if (mb > 500) s += 8
  else s += 3
  const br = (src.bitrate || 0) / 1000000
  if (br > 20) s += 10
  else if (br > 10) s += 7
  else if (br > 5) s += 5
  else s += 2
  return s
}

export function bestSource(item) {
  if (!item.sources || item.sources.length < 2) return null
  return [...item.sources].sort((a, b) => srcScore(b) - srcScore(a))[0]
}

export function isBest(item, src) {
  const b = bestSource(item)
  return b && b.path === src.path
}

export function scoreColor(s) {
  return s >= 70 ? 'var(--color-success)' : s >= 50 ? 'var(--color-warning)' : 'var(--color-error)'
}

export function formatBytes(b) {
  if (!b) return '0 Mo'
  if (b > 1073741824) return (b / 1073741824).toFixed(1) + ' Go'
  return (b / 1048576).toFixed(0) + ' Mo'
}

export function fmtDate(d) {
  if (!d) return ''
  return localizedDate(new Date(d), {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  })
}

export function reclaimableFor(item) {
  if (item.sources.length < 2) return '0 Mo'
  const best = bestSource(item)
  const waste = item.sources
    .filter(s => s.path !== best?.path)
    .reduce((a, s) => a + (s.size_bytes || 0), 0)
  return formatBytes(waste)
}

// Sources to delete for one item given the ordered rule list (first rule that
// resolves a "keep" target wins; falls back to the highest-scoring source).
export function getDeleteTargets(item, rules) {
  if (item.sources.length < 2 || !rules.length) return []
  let keep = null
  for (const rule of rules) {
    if (rule.field === 'keep_largest')
      keep = [...item.sources].sort((a, b) => (b.size_bytes || 0) - (a.size_bytes || 0))[0]
    else if (rule.field === 'keep_smallest')
      keep = [...item.sources].sort((a, b) => (a.size_bytes || 0) - (b.size_bytes || 0))[0]
    else if (rule.field === 'resolution' && rule.value) {
      const minH =
        rule.value === '4K' ? 2100 : rule.value === '1080p' ? 1000 : rule.value === '720p' ? 700 : 0
      keep = [...item.sources]
        .filter(s => (s.height || 0) >= minH)
        .sort((a, b) => (b.height || 0) - (a.height || 0))[0]
    } else if (rule.field === 'codec' && rule.value) {
      const val = rule.value.toUpperCase()
      keep = item.sources.find(s => (s.codec || '').toUpperCase().includes(val))
    }
    if (keep) break
  }
  if (!keep) keep = bestSource(item)
  if (!keep) return []
  return item.sources.filter(s => s.path !== keep.path)
}
