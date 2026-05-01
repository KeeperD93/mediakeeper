/**
 * TMDB media-type discriminator.
 *
 * Backend payloads expose the value on either `media_type` (TMDB payloads,
 * catalogue responses) or `type` (Emby-native payloads). The helpers below
 * normalise the lookup so callers don't have to branch on the field name.
 */
export const MEDIA_TYPE = Object.freeze({
  MOVIE: 'movie',
  TV: 'tv',
} as const)

export type MediaType = (typeof MEDIA_TYPE)[keyof typeof MEDIA_TYPE]

type MediaLike = { media_type?: string; type?: string } | null | undefined

export const isMovie = (item: MediaLike): boolean =>
  item?.media_type === MEDIA_TYPE.MOVIE || item?.type === MEDIA_TYPE.MOVIE

export const isTv = (item: MediaLike): boolean =>
  item?.media_type === MEDIA_TYPE.TV || item?.type === MEDIA_TYPE.TV
