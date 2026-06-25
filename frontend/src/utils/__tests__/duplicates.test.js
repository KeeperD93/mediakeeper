import { describe, expect, it } from 'vitest'
import {
  bestSource,
  doubKey,
  formatBytes,
  getDeleteTargets,
  isBest,
  reclaimableFor,
  scoreColor,
  srcScore,
} from '@/utils/duplicates'

const hi = { path: '/1', height: 2160, codec: 'HEVC', size_bytes: 8e9, bitrate: 25e6 }
const lo = { path: '/2', height: 1080, codec: 'H264', size_bytes: 4e9 }

describe('srcScore', () => {
  it('rewards higher resolution, modern codec, size and bitrate', () => {
    expect(srcScore(hi)).toBe(90) // 40 + 25 + 15 + 10
    expect(srcScore(lo)).toBe(59) // 30 + 15 + 12 + 2 (no bitrate)
  })
  it('floors an empty source to the minimum weights', () => {
    expect(srcScore({})).toBe(15) // 5 + 5 + 3 + 2
  })
})

describe('bestSource / isBest', () => {
  it('picks the highest-scoring source', () => {
    expect(bestSource({ sources: [lo, hi] })).toBe(hi)
  })
  it('returns null when there is less than two sources', () => {
    expect(bestSource({ sources: [hi] })).toBeNull()
    expect(bestSource({ sources: [] })).toBeNull()
  })
  it('matches the best source by path', () => {
    const item = { sources: [hi, lo] }
    expect(isBest(item, hi)).toBe(true)
    expect(isBest(item, lo)).toBe(false)
  })
})

describe('scoreColor', () => {
  it('maps score bands to theme tokens', () => {
    expect(scoreColor(70)).toBe('var(--color-success)')
    expect(scoreColor(50)).toBe('var(--color-warning)')
    expect(scoreColor(49)).toBe('var(--color-error)')
  })
})

describe('formatBytes', () => {
  it('formats falsy, megabyte and gigabyte ranges', () => {
    expect(formatBytes(0)).toBe('0 Mo')
    expect(formatBytes(524288000)).toBe('500 Mo')
    expect(formatBytes(2e9)).toBe('1.9 Go')
  })
})

describe('doubKey', () => {
  it('combines id and source count', () => {
    expect(doubKey({ id: 'm1', sources: [1, 2] })).toBe('m1_2')
  })
})

describe('reclaimableFor', () => {
  it('sums the non-best sources', () => {
    expect(reclaimableFor({ sources: [hi, lo] })).toBe('3.7 Go') // 4e9 wasted
  })
  it('returns zero for a single source', () => {
    expect(reclaimableFor({ sources: [hi] })).toBe('0 Mo')
  })
})

describe('getDeleteTargets', () => {
  const item = { sources: [hi, lo] }
  it('keeps the largest / smallest on size rules', () => {
    expect(getDeleteTargets(item, [{ field: 'keep_largest' }])).toEqual([lo])
    expect(getDeleteTargets(item, [{ field: 'keep_smallest' }])).toEqual([hi])
  })
  it('keeps the highest qualifying resolution', () => {
    expect(getDeleteTargets(item, [{ field: 'resolution', value: '1080p' }])).toEqual([lo])
  })
  it('keeps the matching codec', () => {
    expect(getDeleteTargets(item, [{ field: 'codec', value: 'H264' }])).toEqual([hi])
  })
  it('falls back to the best source when no rule resolves', () => {
    expect(getDeleteTargets(item, [{ field: 'codec', value: 'AV1' }])).toEqual([lo])
  })
  it('returns nothing without rules or with a single source', () => {
    expect(getDeleteTargets(item, [])).toEqual([])
    expect(getDeleteTargets({ sources: [hi] }, [{ field: 'keep_largest' }])).toEqual([])
  })
})
