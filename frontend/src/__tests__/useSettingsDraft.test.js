/**
 * Covers the Configuration screen draft: it loads the settings, marks only the
 * keys the admin actually changed as dirty, PATCHes just those on save, and
 * reverts cleanly on reset.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'

const apiGet = vi.fn()
const apiPatch = vi.fn()
const showToast = vi.fn()
vi.mock('@/composables/useApi', () => ({ useApi: () => ({ apiGet, apiPatch }) }))
vi.mock('@/composables/useToast', () => ({ useToast: () => ({ showToast }) }))
vi.mock('@/constants/toast', () => ({ TOAST_TYPE: { ERR: 'err', OK: 'ok' } }))
vi.mock('vue-i18n', () => ({ useI18n: () => ({ t: k => k }) }))

import { useSettingsDraft } from '@/composables/portal/useSettingsDraft'

const SETTINGS = {
  anonymize_requests: false,
  allow_adult_requests: false,
  'requests.auto_cleanup_days': 0,
  'chat.retention_days': 365,
  hero_trend_count: 10,
  'events.max_participants_min': 5,
  'events.max_participants_max': 20,
  default_language: '',
}

beforeEach(() => {
  apiGet.mockReset().mockResolvedValue({ ...SETTINGS })
  apiPatch.mockReset().mockResolvedValue({ ...SETTINGS })
  showToast.mockClear()
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

  it('marks an emptied numeric field invalid and blocks save', async () => {
    const d = useSettingsDraft()
    await d.load()

    d.draft.hero_trend_count = ''
    expect(d.invalid.value).toBe(true)

    await d.save()
    expect(apiPatch).not.toHaveBeenCalled()
  })

  it('surfaces a toast when the save request fails', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
    const d = useSettingsDraft()
    await d.load()

    d.draft.hero_trend_count = 12
    apiPatch.mockRejectedValueOnce(new Error('500'))
    await d.save()

    expect(showToast).toHaveBeenCalled()
  })

  it('flags out-of-range numeric values invalid and blocks save (over-max, negative, float)', async () => {
    const d = useSettingsDraft()
    await d.load()

    for (const bad of [21, -1, 10.5]) {
      d.draft.hero_trend_count = bad
      expect(d.invalid.value).toBe(true)
    }

    await d.save()
    expect(apiPatch).not.toHaveBeenCalled()
  })

  it('surfaces a toast when the initial load fails', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
    apiGet.mockRejectedValueOnce(new Error('500'))
    const d = useSettingsDraft()
    await d.load()

    expect(showToast).toHaveBeenCalled()
    expect(d.loaded.value).toBe(false)
  })
})
