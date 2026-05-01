/**
 * Trailer provenance.
 *
 * `emby`    — local trailer strm/file served through the Emby proxy.
 * `youtube` — YouTube embed fetched via TMDB's `videos` endpoint.
 * `tracked` — MediaKeeper-tracked upcoming release (pre-Emby availability).
 */
export const TRAILER_SOURCE = Object.freeze({
  EMBY: 'emby',
  YOUTUBE: 'youtube',
  TRACKED: 'tracked',
} as const)

export type TrailerSource = (typeof TRAILER_SOURCE)[keyof typeof TRAILER_SOURCE]
