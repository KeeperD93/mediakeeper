/** Why a watched title pays no watch XP, as the recalculation summary names it. */
export const WATCH_XP_SKIP = Object.freeze({
  BEFORE_LEDGER: 'before_ledger',
  ERASED: 'erased',
  EXCLUDED: 'excluded',
  PARALLEL: 'parallel',
  NO_ACCOUNT: 'no_account',
  NOT_EARNING: 'not_earning',
  COOLDOWN: 'cooldown',
} as const)

export type WatchXpSkip = (typeof WATCH_XP_SKIP)[keyof typeof WATCH_XP_SKIP]

/** Why a player loses all their watch XP. */
export const WATCH_XP_LOST = Object.freeze({
  NO_STATS: 'no_stats',
  NO_END: 'no_end',
  NOT_DUE: 'not_due',
} as const)

export type WatchXpLost = (typeof WATCH_XP_LOST)[keyof typeof WATCH_XP_LOST]
