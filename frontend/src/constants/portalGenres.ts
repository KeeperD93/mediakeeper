/**
 * Genres a viewer can mark as favourite (Settings › Preferences, first-login wizard).
 * `label` names the locale key `portal.genres.<label>`; `ids` are the TMDB genres it
 * stands for (movie and TV ones), all stored in `favorite_genres`.
 */
export interface GenrePick {
  label: string
  ids: readonly number[]
  emoji: string
  color: string
}

export const GENRE_PICKER: readonly GenrePick[] = Object.freeze([
  { label: 'action', ids: [28, 10759], emoji: '💥', color: '#ef4444' },
  { label: 'aventure', ids: [12], emoji: '⚔️', color: '#f97316' },
  { label: 'animation', ids: [16], emoji: '✏️', color: '#a78bfa' },
  { label: 'comedie', ids: [35], emoji: '😂', color: '#fbbf24' },
  { label: 'crime', ids: [80], emoji: '🔫', color: '#dc2626' },
  { label: 'documentaire', ids: [99], emoji: '🎥', color: '#22c55e' },
  { label: 'drame', ids: [18], emoji: '🎭', color: '#3b82f6' },
  { label: 'familial', ids: [10751], emoji: '👨‍👩‍👧', color: '#22c55e' },
  { label: 'fantastique', ids: [14], emoji: '🧙', color: '#8b5cf6' },
  { label: 'guerre', ids: [10752, 10768], emoji: '⚔️', color: '#7c2d12' },
  { label: 'histoire', ids: [36], emoji: '🏛️', color: '#b45309' },
  { label: 'horreur', ids: [27], emoji: '😱', color: '#991b1b' },
  { label: 'mystere', ids: [9648], emoji: '🔍', color: '#6366f1' },
  { label: 'musique', ids: [10402], emoji: '🎵', color: '#c084fc' },
  { label: 'romance', ids: [10749], emoji: '❤️', color: '#ec4899' },
  { label: 'scienceFiction', ids: [878, 10765], emoji: '🚀', color: '#38bdf8' },
  { label: 'thriller', ids: [53], emoji: '😰', color: '#64748b' },
  { label: 'western', ids: [37], emoji: '🤠', color: '#a16207' },
])

export const isGenrePicked = (genre: GenrePick, picked: readonly number[]): boolean =>
  genre.ids.some(id => picked.includes(id))

/** `picked` with the genre's ids added, or all of them removed when it was picked. */
export const toggleGenrePick = (genre: GenrePick, picked: readonly number[]): number[] =>
  isGenrePicked(genre, picked)
    ? picked.filter(id => !genre.ids.includes(id))
    : [...picked, ...genre.ids]
