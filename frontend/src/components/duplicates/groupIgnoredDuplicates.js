/**
 * Group ignored-duplicate entries by series for the "Ignorés" tab.
 *
 * Movies pass through as standalone rows; episodes from the same series
 * collapse into a single row with inline season/episode badges. The
 * episode regex matches the title format produced by the backend duplicate
 * builder ("Series - S04E20 - Episode title").
 */
const EP_RE = /^(.+?)\s+-\s+S(\d+)E(\d+)(?:\s+-\s+.+)?$/i

export function groupIgnoredDuplicates(items) {
  if (!Array.isArray(items)) return []
  const out = []
  const seriesMap = new Map()
  for (const it of items) {
    if (!it) continue
    const title = it.title || ''
    const m = title.match(EP_RE)
    if (m) {
      const name = m[1].trim()
      const season = Number(m[2])
      const episode = Number(m[3])
      let group = seriesMap.get(name)
      if (!group) {
        group = { type: 'series', name, eps: [], keys: [] }
        seriesMap.set(name, group)
        out.push(group)
      }
      group.eps.push({ key: it.key, season, episode })
      group.keys.push(it.key)
    } else {
      out.push({
        type: 'movie',
        name: title || it.key,
        key: it.key,
        keys: [it.key],
      })
    }
  }
  for (const g of seriesMap.values()) {
    g.eps.sort((a, b) => a.season - b.season || a.episode - b.episode)
  }
  return out
}
