import { describe, it, expect } from 'vitest'
import { groupIgnoredDuplicates } from '@/components/duplicates/groupIgnoredDuplicates'

const ep = (key, title) => ({ key, title })

describe('groupIgnoredDuplicates', () => {
  it('groups episodes from the same series under one row', () => {
    const out = groupIgnoredDuplicates([
      ep('100_2', 'My Show - S04E20 - Pilot'),
      ep('101_2', 'My Show - S04E21 - Second'),
      ep('102_2', 'My Show - S05E01 - Third'),
    ])
    expect(out).toHaveLength(1)
    expect(out[0].type).toBe('series')
    expect(out[0].name).toBe('My Show')
    expect(out[0].eps).toEqual([
      { key: '100_2', season: 4, episode: 20 },
      { key: '101_2', season: 4, episode: 21 },
      { key: '102_2', season: 5, episode: 1 },
    ])
    expect(out[0].keys).toEqual(['100_2', '101_2', '102_2'])
  })

  it('keeps movies as standalone rows', () => {
    const out = groupIgnoredDuplicates([
      ep('200_3', 'Inception'),
      ep('201_2', 'The Matrix'),
    ])
    expect(out).toHaveLength(2)
    expect(out.every(g => g.type === 'movie')).toBe(true)
    expect(out.map(g => g.name)).toEqual(['Inception', 'The Matrix'])
  })

  it('mixes series and movies in input order', () => {
    const out = groupIgnoredDuplicates([
      ep('1_2', 'Inception'),
      ep('2_2', 'My Show - S01E01 - A'),
      ep('3_2', 'The Matrix'),
      ep('4_2', 'My Show - S01E02 - B'),
    ])
    expect(out).toHaveLength(3)
    expect(out[0]).toMatchObject({ type: 'movie', name: 'Inception' })
    expect(out[1]).toMatchObject({ type: 'series', name: 'My Show' })
    expect(out[1].eps).toHaveLength(2)
    expect(out[2]).toMatchObject({ type: 'movie', name: 'The Matrix' })
  })

  it('sorts episodes by season then episode', () => {
    const out = groupIgnoredDuplicates([
      ep('a', 'Show - S02E05 - z'),
      ep('b', 'Show - S01E10 - z'),
      ep('c', 'Show - S01E01 - z'),
    ])
    expect(out[0].eps.map(e => `${e.season}-${e.episode}`)).toEqual([
      '1-1',
      '1-10',
      '2-5',
    ])
  })

  it('falls back to the key when title is empty', () => {
    const out = groupIgnoredDuplicates([{ key: 'orphan_1', title: '' }])
    expect(out).toEqual([
      { type: 'movie', name: 'orphan_1', key: 'orphan_1', keys: ['orphan_1'] },
    ])
  })

  it('returns an empty array for non-array input', () => {
    expect(groupIgnoredDuplicates(null)).toEqual([])
    expect(groupIgnoredDuplicates(undefined)).toEqual([])
    expect(groupIgnoredDuplicates('nope')).toEqual([])
  })
})
