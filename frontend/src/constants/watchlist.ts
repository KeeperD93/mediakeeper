/**
 * Watchlist domain enums.
 *
 * EPISODE_STATUS is the per-episode download state computed by the
 * tracking scheduler (stored on `watchlist_series.episodes[].status`).
 *
 * SERIES_STATUS mirrors the raw TMDB show status string — the Capitalized
 * casing is imposed by the TMDB API and must be preserved when comparing
 * against `series.status`. `hiatus` is a MediaKeeper-internal override
 * used by the tracking heuristic when a show goes quiet without TMDB
 * flipping it to `Ended`.
 */
export const EPISODE_STATUS = Object.freeze({
  MISSING: 'missing',
  PRESENT: 'present',
  IGNORED: 'ignored',
} as const)

export type EpisodeStatus = (typeof EPISODE_STATUS)[keyof typeof EPISODE_STATUS]

export const SERIES_STATUS = Object.freeze({
  ENDED: 'Ended',
  ONGOING: 'Returning Series',
  HIATUS: 'hiatus',
  CANCELED: 'Canceled',
} as const)

export type SeriesStatus = (typeof SERIES_STATUS)[keyof typeof SERIES_STATUS]
