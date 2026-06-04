import { describe, it, expect } from 'vitest'

import { tmdbWebUrl } from '@/utils/tmdb'

describe('tmdbWebUrl', () => {
  it('appends the viewer locale as the language param', () => {
    expect(tmdbWebUrl('movie', 603, 'en')).toBe('https://www.themoviedb.org/movie/603?language=en')
    expect(tmdbWebUrl('tv', 1399, 'fr')).toBe('https://www.themoviedb.org/tv/1399?language=fr')
  })

  it('returns a neutral link when no locale is given', () => {
    expect(tmdbWebUrl('movie', 5, '')).toBe('https://www.themoviedb.org/movie/5')
    expect(tmdbWebUrl('movie', 5)).toBe('https://www.themoviedb.org/movie/5')
  })

  it('defaults the media type to tv', () => {
    expect(tmdbWebUrl(undefined, 7, 'en')).toBe('https://www.themoviedb.org/tv/7?language=en')
  })
})
