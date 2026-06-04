/**
 * Maps each scheduler task key to a thematic category surfaced in the
 * admin Settings → Scheduler panel. Categories let the panel group the
 * 11 visible tasks into 4 sections (vs a flat alphabetical list) so an
 * admin can scan all tasks without scrolling on desktop.
 *
 * Unknown task keys (e.g. a future task added backend-side before the
 * frontend knows about it) fall back to "system" so the row still
 * renders — it just lands in the catch-all section.
 */
export type SchedulerCategoryKey = 'media' | 'portal' | 'users' | 'system'

interface SchedulerCategory {
  key: SchedulerCategoryKey
  labelKey: string
  tasks: readonly string[]
}

export const SCHEDULER_CATEGORIES: Readonly<Record<SchedulerCategoryKey, SchedulerCategory>> =
  Object.freeze({
    media: Object.freeze({
      key: 'media' as const,
      labelKey: 'scheduler.categories.media',
      tasks: Object.freeze([
        'watchlist_scan',
        'duplicates_scan',
        'emby_refresh',
        'healthcheck_scan',
        'subtitle_auto',
      ]),
    }),
    portal: Object.freeze({
      key: 'portal' as const,
      labelKey: 'scheduler.categories.portal',
      tasks: Object.freeze(['cleanup_available_requests', 'emby_recent_scan', 'emby_full_scan']),
    }),
    users: Object.freeze({
      key: 'users' as const,
      labelKey: 'scheduler.categories.users',
      tasks: Object.freeze(['expire_users', 'gdpr_purge']),
    }),
    system: Object.freeze({
      key: 'system' as const,
      labelKey: 'scheduler.categories.system',
      tasks: Object.freeze(['log_cleanup', 'backup_auto', 'clear_image_cache']),
    }),
  })

export const CATEGORY_ORDER: readonly SchedulerCategoryKey[] = Object.freeze([
  'media',
  'portal',
  'users',
  'system',
])

/**
 * Task keys that exist backend-side but should NOT be surfaced in the
 * admin UI (typically internal housekeeping). Notifications runs every
 * minute and admins have no reason to act on it.
 */
export const HIDDEN_TASK_KEYS: readonly string[] = Object.freeze(['notifications'])

export function categoryForTaskKey(taskKey: string): SchedulerCategoryKey {
  for (const cat of CATEGORY_ORDER) {
    if (SCHEDULER_CATEGORIES[cat].tasks.includes(taskKey)) return cat
  }
  return 'system'
}

interface TaskLike {
  key: string
}

interface CategoryGroup<T extends TaskLike> {
  category: SchedulerCategoryKey
  tasks: T[]
}

/**
 * Build the array consumed by SchedulerTaskList.vue: one entry per
 * non-empty category, in CATEGORY_ORDER, each carrying its visible tasks.
 */
export function groupTasksByCategory<T extends TaskLike>(tasks: T[]): CategoryGroup<T>[] {
  const buckets: Record<SchedulerCategoryKey, T[]> = {
    media: [],
    portal: [],
    users: [],
    system: [],
  }
  for (const t of tasks) {
    buckets[categoryForTaskKey(t.key)].push(t)
  }
  return CATEGORY_ORDER.map(cat => ({ category: cat, tasks: buckets[cat] })).filter(
    g => g.tasks.length > 0,
  )
}
