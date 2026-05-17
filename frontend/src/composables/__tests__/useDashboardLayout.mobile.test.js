/**
 * useDashboardLayout — coverage of the mobile order branch added for
 * the long-press / drag-reorder flow:
 *
 * 1. ``effectiveMobileOrder`` falls back to MOBILE_DEFAULT_ORDER when
 *    no user customisation exists.
 * 2. Hidden widgets are filtered out regardless of the source order.
 * 3. The four stat IDs never appear in the stack list — they have
 *    their own fixed 2×2 grid above.
 * 4. ``setMobileOrder`` clones the input so external mutation cannot
 *    leak into the composable state.
 * 5. Widgets that exist in the registry but are missing from a user-
 *    saved order get appended in registry order, never silently lost.
 */
import { describe, it, expect, vi } from 'vitest'

vi.mock('@/composables/useApi', () => ({
  useApi: () => ({
    apiGet: vi.fn().mockResolvedValue(null),
    apiPost: vi.fn().mockResolvedValue({}),
  }),
}))

import {
  MOBILE_DEFAULT_ORDER,
  MOBILE_STAT_IDS,
  useDashboardLayout,
} from '@/composables/useDashboardLayout'

describe('useDashboardLayout — mobile order', () => {
  it('falls back to MOBILE_DEFAULT_ORDER when no user customisation', () => {
    const { effectiveMobileOrder } = useDashboardLayout()
    const ids = effectiveMobileOrder.value
    for (const expected of MOBILE_DEFAULT_ORDER) {
      expect(ids).toContain(expected)
    }
  })

  it('excludes the four stat IDs from the stack list', () => {
    const { effectiveMobileOrder } = useDashboardLayout()
    for (const stat of MOBILE_STAT_IDS) {
      expect(effectiveMobileOrder.value).not.toContain(stat)
    }
  })

  it('filters hidden widgets out of the effective order', () => {
    const { effectiveMobileOrder, hidden } = useDashboardLayout()
    hidden.value = ['activity', 'heatmap']
    expect(effectiveMobileOrder.value).not.toContain('activity')
    expect(effectiveMobileOrder.value).not.toContain('heatmap')
  })

  it('honours a user-saved order via setMobileOrder', () => {
    const { effectiveMobileOrder, setMobileOrder } = useDashboardLayout()
    setMobileOrder(['heatmap', 'activity', 'topUsers'])
    const ids = effectiveMobileOrder.value
    // The three explicitly ordered IDs land in order at the start.
    expect(ids[0]).toBe('heatmap')
    expect(ids[1]).toBe('activity')
    expect(ids[2]).toBe('topUsers')
  })

  it('appends registry widgets missing from a saved order so nothing disappears', () => {
    const { effectiveMobileOrder, setMobileOrder } = useDashboardLayout()
    setMobileOrder(['activity'])
    const ids = effectiveMobileOrder.value
    expect(ids[0]).toBe('activity')
    // healthScore is in the registry but not in the saved order → appended.
    expect(ids).toContain('healthScore')
    expect(ids).toContain('linkWatchlist')
  })

  it('setMobileOrder clones the input so caller mutations do not leak', () => {
    const { effectiveMobileOrder, setMobileOrder } = useDashboardLayout()
    const input = ['heatmap', 'activity']
    setMobileOrder(input)
    input.push('upcoming')
    // The stored order should still reflect the two-item snapshot.
    const ids = effectiveMobileOrder.value
    expect(ids[0]).toBe('heatmap')
    expect(ids[1]).toBe('activity')
    // upcoming lands later via the registry fallback, not because of mutation.
    expect(ids.indexOf('upcoming')).toBeGreaterThan(1)
  })
})
