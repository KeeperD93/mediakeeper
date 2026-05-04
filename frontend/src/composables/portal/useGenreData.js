/**
 * Genre presentation helpers — i18n keys, slugs, emojis, colors used by
 * the profile page (genre cards + recommendation sections).
 *
 * Genre IDs come from TMDB. Some IDs differ between movie/tv but share a label
 * (e.g. 28 Action movie vs 10759 Action & Adventure for TV).
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { isMovie, isTv } from '@/constants/media'

export const GENRE_I18N = {
  28: 'action',
  35: 'comedie',
  18: 'drame',
  53: 'thriller',
  12: 'aventure',
  27: 'horreur',
  878: 'scienceFiction',
  16: 'animation',
  14: 'fantastique',
  10751: 'familial',
  99: 'documentaire',
  9648: 'mystere',
  80: 'crime',
  10749: 'romance',
  10759: 'action',
  10765: 'scienceFiction',
  36: 'histoire',
  37: 'western',
  10752: 'guerre',
  10402: 'musique',
  10770: 'telefilm',
  10762: 'enfants',
  10763: 'info',
  10764: 'realite',
  10766: 'feuilleton',
  10767: 'talkShow',
  10768: 'guerrePolitique',
}
export const GENRE_SLUG = {
  28: 'action',
  35: 'comedie',
  18: 'drame',
  53: 'thriller',
  12: 'aventure',
  27: 'horreur',
  878: 'science-fiction',
  16: 'animation',
  14: 'fantastique',
  10751: 'familial',
  99: 'documentaire',
  9648: 'mystere',
  10759: 'action',
  10765: 'science-fiction',
  36: 'histoire',
  37: 'western',
  10752: 'guerre',
  10402: 'musique',
}
export const GENRE_EMOJI = {
  28: '💥',
  35: '😂',
  18: '🎭',
  53: '😰',
  12: '⚔️',
  27: '😱',
  878: '🚀',
  16: '✏️',
  14: '🧙',
  10751: '👨‍👩‍👧',
  99: '🎥',
  9648: '🔍',
  80: '🔫',
  10749: '❤️',
  10759: '💥',
  10765: '🚀',
  36: '🏛️',
  37: '🤠',
  10752: '⚔️',
  10402: '🎵',
  10770: '📺',
  10762: '🧸',
  10763: '📰',
  10764: '🎬',
  10766: '💔',
  10767: '🎙️',
  10768: '🪖',
}
/* TMDB genre id → Lucide icon name. Resolved to components by the caller
 * via a local registry so we can tree-shake icons we actually ship. */
export const GENRE_ICON = {
  28: 'Zap', // Action
  35: 'Laugh', // Comedy
  18: 'Drama', // Drama
  53: 'AlertTriangle', // Thriller
  12: 'Compass', // Adventure
  27: 'Ghost', // Horror
  878: 'Rocket', // Science-fiction
  16: 'Palette', // Animation
  14: 'Sparkles', // Fantasy
  10751: 'Users', // Family
  99: 'Camera', // Documentary
  9648: 'Search', // Mystery
  80: 'Shield', // Crime
  10749: 'Heart', // Romance
  10759: 'Zap', // Action & Adventure (TV)
  10765: 'Rocket', // SF & Fantasy (TV)
  36: 'Landmark', // History
  37: 'Mountain', // Western
  10752: 'Swords', // War
  10402: 'Music', // Music
  10770: 'Tv', // TV Movie
  10762: 'Baby', // Kids
  10763: 'Newspaper', // News
  10764: 'Radio', // Reality
  10766: 'HeartCrack', // Soap
  10767: 'Mic', // Talk-show
  10768: 'Flag', // War & Politics
}
export const GENRE_COLOR = {
  28: '#ef4444',
  35: '#fbbf24',
  18: '#3b82f6',
  53: '#64748b',
  12: '#f97316',
  27: '#991b1b',
  878: '#38bdf8',
  16: '#a78bfa',
  14: '#8b5cf6',
  10751: '#22c55e',
  99: '#22c55e',
  9648: '#6366f1',
  80: '#dc2626',
  10749: '#ec4899',
  10759: '#ef4444',
  10765: '#38bdf8',
  36: '#b45309',
  37: '#a16207',
  10752: '#7c2d12',
  10402: '#c084fc',
  10770: '#94a3b8',
  10762: '#fbbf24',
  10763: '#0ea5e9',
  10764: '#14b8a6',
  10766: '#f472b6',
  10767: '#60a5fa',
  10768: '#64748b',
}

export function useGenreData(recoItems, genreIds, excludedItems) {
  const { t } = useI18n()

  function genreName(id) {
    const key = GENRE_I18N[id]
    if (!key) return `Genre ${id}`
    const full = `portal.genres.${key}`
    const translated = t(full)
    return translated !== full ? translated : key
  }

  // "Because you like X" sections — top 2 genres with at least 3
  // matching items. Items inside each section are sorted by TMDB
  // popularity descending so the most relevant titles land first (B5).
  // `excludedItems` (optional ref to an array) holds titles already
  // surfaced in other profile carousels (Recommended for you, Because
  // you watched X). Excluding them here avoids showing the
  // exact same poster list under "Because you like {genre}" when
  // the user's dominant genre happens to drive the base reco engine.
  const genreSections = computed(() => {
    const top = (genreIds.value || []).slice(0, 2)
    const sections = []
    const used = new Set()
    const excluded = new Set()
    for (const it of excludedItems?.value || []) {
      const id = it.tmdb_id || it.id
      if (id) excluded.add(id)
    }
    for (const gid of top) {
      const matching = (recoItems.value || []).filter(it => {
        const id = it.tmdb_id || it.id
        if (used.has(id) || excluded.has(id)) return false
        return (it.genres || []).includes(gid)
      })
      if (matching.length < 3) continue
      const sorted = matching.slice().sort((a, b) => (b.popularity || 0) - (a.popularity || 0))
      const capped = sorted.slice(0, 20)
      capped.forEach(it => used.add(it.tmdb_id || it.id))
      sections.push({
        genreId: gid,
        slug: GENRE_SLUG[gid] || 'action',
        title: t('portal.reco.becauseYouLike', { genre: genreName(gid) }),
        items: capped,
      })
    }
    return sections
  })

  const movieItems = computed(() => (recoItems.value || []).filter(isMovie).slice(0, 20))
  const tvItems = computed(() => (recoItems.value || []).filter(isTv).slice(0, 20))

  return { genreName, genreSections, movieItems, tvItems, GENRE_COLOR, GENRE_EMOJI, GENRE_ICON }
}
