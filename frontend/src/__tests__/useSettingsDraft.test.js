/**
 * Covers the Configuration screen draft: it loads the settings, marks only the
 * keys the admin actually changed as dirty, PATCHes just those on save, and
 * reverts cleanly on reset.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'

const apiGet = vi.fn()
const apiPatch = vi.fn()
vi.mock('@/composables/useApi', () => ({ useApi: () => ({ apiGet, apiPatch }) }))

import { useSettingsDraft } from '@/composables/portal/useSettingsDraft'

const SETTINGS = {
  anonymize_requests: false,
  allow_adult_requests: false,
  'requests.auto_cleanup_days': 0,
  hero_trend_count: 10,
  'events.max_participants_min': 5,
  'events.max_participants_max': 20,
  default_language: '',
}

beforeEach(() => {
  apiGet.mockReset().mockResolvedValue({ ...SETTINGS })
  apiPatch.mockReset().mockResolvedValue({ ...SETTINGS })
})

describe('useSettingsDraft', () => {
  it('seeds typed defaults before load (no undefined-bound controls)', () => {
    const d = useSettingsDraft()
    expect(typeof d.draft.anonymize_requests).toBe('boolean')
    expect(typeof d.draft.hero_trend_count).toBe('number')
    expect(d.dirty.value).toBe(false)
  })

  it('loads cleanly, then tracks and PATCHes only the changed keys', async () => {
    const d = useSettingsDraft()
    await d.load()
    expect(d.dirty.value).toBe(false)

    d.draft.hero_trend_count = 12
    d.draft.anonymize_requests = true
    expect(d.dirty.value).toBe(true)
    expect([...d.dirtyKeys.value].sort()).toEqual(['anonymize_requests', 'hero_trend_count'])

    await d.save()
    expect(apiPatch).toHaveBeenCalledWith('/api/portal/admin/settings', {
      anonymize_requests: true,
      hero_trend_count: 12,
    })
  })

  it('reset reverts the draft to the last-saved snapshot', async () => {
    const d = useSettingsDraft()
    await d.load()

    d.draft.hero_trend_count = 99
    expect(d.dirty.value).toBe(true)

    d.reset()
    expect(d.draft.hero_trend_count).toBe(10)
    expect(d.dirty.value).toBe(false)
  })

  it('save is a no-op when nothing changed', async () => {
    const d = useSettingsDraft()
    await d.load()
    await d.save()
    expect(apiPatch).not.toHaveBeenCalled()
  })
})
