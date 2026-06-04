const TMDB_WEB_BASE = 'https://www.themoviedb.org'

/**
 * Build a themoviedb.org detail URL carrying the viewer's app language so the
 * page opens in the same language as MediaKeeper. `locale` is the 2-letter app
 * locale (useI18n's `locale.value`); TMDB still falls back to the visitor's own
 * browser/account for its surrounding chrome, so this mainly aligns the shown
 * title + overview. Falls back to a neutral link when no locale is given.
 */
export function tmdbWebUrl(mediaType, tmdbId, locale) {
  const base = `${TMDB_WEB_BASE}/${mediaType || 'tv'}/${tmdbId}`
  return locale ? `${base}?language=${locale}` : base
}
