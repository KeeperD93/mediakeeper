import { describe, it, expect } from 'vitest'
import { dedupeByTmdb } from '@/components/watchlist/WlSeriesView/dedupeByTmdb'

const entry = (tmdb_id, missing_count, extra = {}) => ({
  tmdb_id,
  missing_count,
  upcoming_count: 0,
  name: extra.name ?? `Series ${tmdb_id}`,
  ...extra,
})

describe('dedupeByTmdb', () => {
  it('collapses entries that share the same tmdb_id', () => {
    const out = dedupeByTmdb([
      entry(42, 5, { series_id: 'A' }),
      entry(42, 5, { series_id: 'B' }),
      entry(99, 2),
    ])
    expect(out).toHaveLength(2)
    expect(out.map(s => s.tmdb_id).sort()).toEqual([42, 99])
  })

  it('keeps the copy with the lowest missing_count', () => {
    const out = dedupeByTmdb([
      entry(42, 12, { series_id: 'incomplete' }),
      entry(42, 3, { series_id: 'complete' }),
      entry(42, 8, { series_id: 'middle' }),
    ])
    expect(out).toHaveLength(1)
    expect(out[0].series_id).toBe('complete')
  })

  it('preserves unique entries unchanged', () => {
    const input = [entry(1, 4), entry(2, 0), entry(3, 7)]
    expect(
      dedupeByTmdb(input)
        .map(s => s.tmdb_id)
        .sort(),
    ).toEqual([1, 2, 3])
  })

  it('passes through entries with no tmdb_id', () => {
    const out = dedupeByTmdb([
      { name: 'Orphan', missing_count: 1 },
      { tmdb_id: null, name: 'Null tmdb', missing_count: 2 },
      entry(7, 3),
    ])
    expect(out).toHaveLength(3)
    expect(out.map(s => s.name).sort()).toEqual(['Null tmdb', 'Orphan', 'Series 7'])
  })

  it('returns an empty array for null / non-array input', () => {
    expect(dedupeByTmdb(null)).toEqual([])
    expect(dedupeByTmdb(undefined)).toEqual([])
    expect(dedupeByTmdb('not an array')).toEqual([])
  })
})
