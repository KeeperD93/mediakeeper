// Genre id → display label + emoji used by the public profile genre
// chips. Extracted from PortalUserProfile.vue so the page file stays
// within its size budget; the values mirror the TMDB id list curated
// in the portal preferences flow.
export const GENRE_LOOKUP = Object.freeze([
  { label: 'action', ids: [28, 10759], emoji: '💥' },
  { label: 'aventure', ids: [12], emoji: '⚔️' },
  { label: 'animation', ids: [16], emoji: '✏️' },
  { label: 'comedie', ids: [35], emoji: '😂' },
  { label: 'crime', ids: [80], emoji: '🔫' },
  { label: 'documentaire', ids: [99], emoji: '🎥' },
  { label: 'drame', ids: [18], emoji: '🎭' },
  { label: 'familial', ids: [10751], emoji: '👨‍👩‍👧' },
  { label: 'fantastique', ids: [14], emoji: '🧙' },
  { label: 'guerre', ids: [10752, 10768], emoji: '⚔️' },
  { label: 'histoire', ids: [36], emoji: '🏛️' },
  { label: 'horreur', ids: [27], emoji: '😱' },
  { label: 'mystere', ids: [9648], emoji: '🔍' },
  { label: 'musique', ids: [10402], emoji: '🎵' },
  { label: 'romance', ids: [10749], emoji: '❤️' },
  { label: 'scienceFiction', ids: [878, 10765], emoji: '🚀' },
  { label: 'thriller', ids: [53], emoji: '😰' },
  { label: 'western', ids: [37], emoji: '🤠' },
])
