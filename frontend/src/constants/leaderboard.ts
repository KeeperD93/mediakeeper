/** Periods of the ranking, as the server names them. */
export const LEADERBOARD_PERIOD = Object.freeze({
  TODAY: 'today',
  WEEK: 'week',
  MONTH: 'month',
  ALL: 'all',
} as const)

export type LeaderboardPeriod = (typeof LEADERBOARD_PERIOD)[keyof typeof LEADERBOARD_PERIOD]

/** The tabs, in the order they are shown. */
export const LEADERBOARD_PERIODS: LeaderboardPeriod[] = [
  LEADERBOARD_PERIOD.TODAY,
  LEADERBOARD_PERIOD.WEEK,
  LEADERBOARD_PERIOD.MONTH,
  LEADERBOARD_PERIOD.ALL,
]

export const LEADERBOARD_PAGE_LIMIT = 100

/** Rows of the ranking card of "My profile", as many as the month the profile brings. */
export const LEADERBOARD_PROFILE_LIMIT = 15
