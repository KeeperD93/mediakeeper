/**
 * Subtitle / audio track enums.
 *
 * STREAM_TYPE is the discriminator on embedded media streams.
 * SUB_LIB_STATUS tags items returned by the subtitle library scanner:
 * missing (no sub track), forced (only forced/partial subs), image_only
 * (PGS / VobSub bitmap subs that can't be searched as text).
 */
export const STREAM_TYPE = Object.freeze({
  AUDIO: 'audio',
  SUBTITLE: 'subtitle',
} as const)

export type StreamType = (typeof STREAM_TYPE)[keyof typeof STREAM_TYPE]

export const SUB_LIB_STATUS = Object.freeze({
  MISSING: 'missing',
  FORCED: 'forced',
  IMAGE_ONLY: 'image_only',
} as const)

export type SubLibStatus = (typeof SUB_LIB_STATUS)[keyof typeof SUB_LIB_STATUS]
