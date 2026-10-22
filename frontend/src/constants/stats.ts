// Statistics vocabulary shared with the backend (backend/api/stats/_exclusions.py).

// How a statistics exclusion matches a title: the whole title, or a part of it.
export const STATS_EXCLUSION_MODE = Object.freeze({ EXACT: 'exact', CONTAINS: 'contains' } as const)
export type StatsExclusionMode = (typeof STATS_EXCLUSION_MODE)[keyof typeof STATS_EXCLUSION_MODE]
