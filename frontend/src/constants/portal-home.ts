/**
 * Static data powering the Portal home page:
 *   - `buildGenres(t)`   : the 12 genre cards (translated labels)
 *   - `buildPlatforms()` : the 13 unified streaming platforms (FR + US)
 *   - `PROVIDER_ID_TO_SLUG` : reverse lookup for the provider detail route
 *
 * Kept separate from PortalHome.vue so the home component stays under
 * 300 lines and so the arrays can be consumed from admin tooling too.
 *
 * IMPORTANT: `PROVIDER_ID_TO_SLUG` must stay in sync with the `providerId`
 * field inside `buildPlatforms()`. If you fix an ID in one, fix it in
 * the other.
 */

/**
 * Minimal translation callable compatible with vue-i18n's `t`. We keep it
 * narrow on purpose — this module only ever passes a single string key.
 */
type TranslateFn = (key: string) => string

export interface PortalGenre {
  key: string
  label: string
  color: string
}

export interface PortalPlatform {
  key: string
  label: string
  logo: string
  color: string
  providerId: number
}

/**
 * 12 TMDB genres, ordered by global popularity (box-office + streaming
 * consumption data). Action and Comedy dominate worldwide, followed by
 * Drama and Thriller. Niche genres (Documentary, Mystery) sit at the
 * end so the first few cards the user sees hold the most content.
 */
export function buildGenres(t: TranslateFn): PortalGenre[] {
  return [
    { key: 'action', label: t('portal.genres.action'), color: 'rgba(239, 68, 68, 0.30)' },
    { key: 'comedie', label: t('portal.genres.comedie'), color: 'rgba(250, 204, 21, 0.30)' },
    { key: 'drame', label: t('portal.genres.drame'), color: 'rgba(99, 102, 241, 0.30)' },
    { key: 'thriller', label: t('portal.genres.thriller'), color: 'rgba(30, 41, 59, 0.55)' },
    { key: 'aventure', label: t('portal.genres.aventure'), color: 'rgba(34, 197, 94, 0.30)' },
    { key: 'horreur', label: t('portal.genres.horreur'), color: 'rgba(15, 23, 42, 0.55)' },
    {
      key: 'science-fiction',
      label: t('portal.genres.scienceFiction'),
      color: 'rgba(56, 189, 248, 0.30)',
    },
    { key: 'animation', label: t('portal.genres.animation'), color: 'rgba(236, 72, 153, 0.30)' },
    {
      key: 'fantastique',
      label: t('portal.genres.fantastique'),
      color: 'rgba(168, 85, 247, 0.30)',
    },
    { key: 'familial', label: t('portal.genres.familial'), color: 'rgba(251, 146, 60, 0.30)' },
    {
      key: 'documentaire',
      label: t('portal.genres.documentaire'),
      color: 'rgba(120, 113, 108, 0.35)',
    },
    { key: 'mystere', label: t('portal.genres.mystere'), color: 'rgba(79, 70, 229, 0.30)' },
  ]
}

/**
 * 13 streaming platforms (internationals + FR + Hulu US) merged into a
 * single scrollable row.
 *
 * Provider IDs are the FR-region TMDB ids (not the US ones — many
 * third-party lists publish US ids by default). To verify / update
 * this table, hit:
 *   GET /api/portal/catalog/watch-providers?region=FR&media_type=movie
 * and look up the provider_name column.
 *
 * All logos live under `/assets/icons/platforms/*.svg` (kebab-case) —
 * a dedicated directory separate from the generic icons (emby.svg,
 * tmdb.svg, mediakeeper.png) to keep platform artwork contained.
 * All logos are monochrome dark-background variants, so no CSS colour
 * hack is needed in CategoryCards.
 */
export function buildPlatforms(): PortalPlatform[] {
  return [
    {
      key: 'netflix',
      label: 'Netflix',
      logo: '/assets/icons/platforms/netflix.svg',
      color: 'rgba(229,9,20,0.25)',
      providerId: 8,
    },
    {
      key: 'prime',
      label: 'Prime Video',
      logo: '/assets/icons/platforms/prime-video.svg',
      color: 'rgba(0,168,225,0.25)',
      providerId: 119,
    },
    {
      key: 'disney',
      label: 'Disney+',
      logo: '/assets/icons/platforms/disney-plus.svg',
      color: 'rgba(17,60,207,0.25)',
      providerId: 337,
    },
    {
      key: 'max',
      label: 'Max',
      logo: '/assets/icons/platforms/max.svg',
      color: 'rgba(89,49,150,0.25)',
      providerId: 1899,
    },
    {
      key: 'apple',
      label: 'Apple TV+',
      logo: '/assets/icons/platforms/apple-tv-plus.svg',
      color: 'rgba(100,100,100,0.25)',
      providerId: 350,
    },
    {
      key: 'paramount',
      label: 'Paramount+',
      logo: '/assets/icons/platforms/paramount-plus.svg',
      color: 'rgba(0,100,210,0.25)',
      providerId: 531,
    },
    {
      key: 'crunchyroll',
      label: 'Crunchyroll',
      logo: '/assets/icons/platforms/crunchyroll.svg',
      color: 'rgba(244,117,33,0.25)',
      providerId: 283,
    },
    {
      key: 'adn',
      label: 'ADN',
      logo: '/assets/icons/platforms/adn.svg',
      color: 'rgba(255,221,51,0.25)',
      providerId: 415,
    },
    {
      key: 'canal',
      label: 'Canal+',
      logo: '/assets/icons/platforms/canal-plus.svg',
      color: 'rgba(0,0,0,0.35)',
      providerId: 381,
    },
    {
      key: 'arte',
      label: 'Arte',
      logo: '/assets/icons/platforms/arte.svg',
      color: 'rgba(236,26,51,0.25)',
      providerId: 234,
    },
    {
      key: 'mubi',
      label: 'MUBI',
      logo: '/assets/icons/platforms/mubi.svg',
      color: 'rgba(30,40,60,0.35)',
      providerId: 11,
    },
    {
      key: 'tf1plus',
      label: 'TF1+',
      logo: '/assets/icons/platforms/tf1-plus.svg',
      color: 'rgba(32,65,130,0.25)',
      providerId: 1754,
    },
    // US-only — TMDB has no FR availability for Hulu, so the dedicated
    // page hits the US watch_region. The tile still shows on FR homes
    // so French users can browse Hulu's catalogue.
    {
      key: 'hulu',
      label: 'Hulu',
      logo: '/assets/icons/platforms/hulu.svg',
      color: 'rgba(28,231,131,0.25)',
      providerId: 15,
    },
  ]
}

/**
 * Reverse lookup: TMDB provider id → route slug. Mirrors the table in
 * PortalProviderPage.vue. MUST stay in sync with `buildPlatforms()`.
 */
export const PROVIDER_ID_TO_SLUG: Readonly<Record<number, string>> = {
  8: 'netflix',
  119: 'prime',
  337: 'disney',
  1899: 'max',
  350: 'apple',
  531: 'paramount',
  283: 'crunchyroll',
  415: 'adn',
  381: 'canal',
  234: 'arte',
  11: 'mubi',
  1754: 'tf1plus',
  15: 'hulu',
}
