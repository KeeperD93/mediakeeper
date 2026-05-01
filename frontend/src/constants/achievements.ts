/**
 * Trophy / achievement enums mirrored from the backend seeder
 * (`backend/app/achievements/*`). Keys kept UPPERCASE, values lowercase.
 *
 * TROPHY_STATUS drives rendering in TrophyGrid / TrophyOverlay / TrophyFx.
 * TROPHY_CATEGORY is the top-level tab grouping on the profile page.
 * TROPHY_TIER maps to the bronze→supreme visual ladder.
 */
export const TROPHY_STATUS = Object.freeze({
  UNLOCKED: 'unlocked',
  LOCKED: 'locked',
  PROGRESS: 'progress',
  SECRET: 'secret',
} as const)

export type TrophyStatus = (typeof TROPHY_STATUS)[keyof typeof TROPHY_STATUS]

export const TROPHY_CATEGORY = Object.freeze({
  MASTERY: 'mastery',
  SKILLS: 'skills',
  COLLECTION: 'collection',
  SOCIAL: 'social',
} as const)

export type TrophyCategory = (typeof TROPHY_CATEGORY)[keyof typeof TROPHY_CATEGORY]

export const TROPHY_TIER = Object.freeze({
  BRONZE: 'bronze',
  SILVER: 'silver',
  GOLD: 'gold',
  PLATINUM: 'platinum',
  DIAMOND: 'diamond',
  MYTHIC: 'mythic',
  SUPREME: 'supreme',
} as const)

export type TrophyTier = (typeof TROPHY_TIER)[keyof typeof TROPHY_TIER]
