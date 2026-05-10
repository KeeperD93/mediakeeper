/**
 * Collapse a watchlist series list so that each `tmdb_id` appears once.
 *
 * Emby may expose the same TV series several times (split versions, multiple
 * libraries) and the cached scan result then carries duplicates. The list
 * view keys on `tmdb_id`, so we keep the entry with the lowest `missing_count`
 * (best Emby copy) and pass through items missing a `tmdb_id` unchanged.
 */
export function dedupeByTmdb(series) {
  if (!Array.isArray(series)) return []
  const byTmdb = new Map()
  const orphans = []
  for (const s of series) {
    if (!s || s.tmdb_id == null) {
      if (s) orphans.push(s)
      continue
    }
    const prev = byTmdb.get(s.tmdb_id)
    if (!prev || (s.missing_count ?? 0) < (prev.missing_count ?? 0)) {
      byTmdb.set(s.tmdb_id, s)
    }
  }
  return [...byTmdb.values(), ...orphans]
}
