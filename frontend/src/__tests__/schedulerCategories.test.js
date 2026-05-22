import { describe, it, expect } from 'vitest'
import {
  SCHEDULER_CATEGORIES,
  CATEGORY_ORDER,
  categoryForTaskKey,
  groupTasksByCategory,
} from '@/constants/schedulerCategories'

describe('schedulerCategories', () => {
  it('exposes 4 categories in a stable order', () => {
    expect(CATEGORY_ORDER).toEqual(['media', 'portal', 'users', 'system'])
    expect(Object.keys(SCHEDULER_CATEGORIES)).toEqual(CATEGORY_ORDER)
  })

  it('every known task key maps to exactly one category', () => {
    const all = CATEGORY_ORDER.flatMap(c => SCHEDULER_CATEGORIES[c].tasks)
    expect(new Set(all).size).toBe(all.length)
  })

  it('routes known task keys to their declared category', () => {
    expect(categoryForTaskKey('watchlist_scan')).toBe('media')
    expect(categoryForTaskKey('cleanup_available_requests')).toBe('portal')
    expect(categoryForTaskKey('expire_users')).toBe('users')
    expect(categoryForTaskKey('backup_auto')).toBe('system')
  })

  it('routes unknown task keys to the system fallback', () => {
    expect(categoryForTaskKey('future_task_not_listed_yet')).toBe('system')
  })

  it('groups tasks while preserving category order', () => {
    const tasks = [
      { key: 'backup_auto' },
      { key: 'watchlist_scan' },
      { key: 'expire_users' },
      { key: 'duplicates_scan' },
    ]
    const grouped = groupTasksByCategory(tasks)
    expect(grouped.map(g => g.category)).toEqual(['media', 'users', 'system'])
    expect(grouped[0].tasks.map(t => t.key)).toEqual(['watchlist_scan', 'duplicates_scan'])
  })

  it('omits empty categories from the result', () => {
    const grouped = groupTasksByCategory([{ key: 'watchlist_scan' }])
    expect(grouped).toHaveLength(1)
    expect(grouped[0].category).toBe('media')
  })

  it('handles an empty input gracefully', () => {
    expect(groupTasksByCategory([])).toEqual([])
  })
})
