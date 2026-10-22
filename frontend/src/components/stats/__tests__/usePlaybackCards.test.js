/**
 * Statistics → General title cards: "most watched" shows the time spent on each
 * title, "popular" the number of different viewers.
 */
import { describe, it, expect } from 'vitest'
import { ref } from 'vue'
import { usePlaybackCards } from '@/components/stats/StatsPlaybackCards/usePlaybackCards'

const HOUR = 36_000_000_000 // ticks
const t = key => key
const ticksToHours = ticks => `${ticks / HOUR}h`

const playback = ref({
  top_movies: [{ name: 'Movie A', item_id: 'm-a', ticks: 2 * HOUR }],
  popular_movies: [{ name: 'Movie A', item_id: 'm-a', users: 2 }],
  top_series: [{ name: 'Series S', ticks: 3 * HOUR }],
  popular_series: [{ name: 'Series S', users: 3 }],
  top_users_hours: [],
  top_users: [],
  by_library: [],
  by_client: [],
})

const cards = () => usePlaybackCards(playback, t, ticksToHours).orderedCards.value
const card = id => cards().find(c => c.id === id)
const value = c => (c.valFn ? c.valFn(c.items[0]) : c.items[0][c.valKey])

describe('usePlaybackCards — title cards', () => {
  it('shows the most watched titles in hours', () => {
    expect(card('top_movies').unit).toBe('common.hours')
    expect(value(card('top_movies'))).toBe('2h')
    expect(card('top_series').unit).toBe('common.hours')
    expect(value(card('top_series'))).toBe('3h')
  })

  it('shows the popular titles in viewers', () => {
    expect(card('popular_movies').unit).toBe('stats.users')
    expect(value(card('popular_movies'))).toBe(2)
    expect(card('popular_series').unit).toBe('stats.users')
    expect(value(card('popular_series'))).toBe(3)
  })
})
