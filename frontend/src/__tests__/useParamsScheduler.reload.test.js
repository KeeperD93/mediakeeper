/**
 * Scheduler tab: back on the tab, an interval changed elsewhere shows up, but never over
 * what the admin is editing.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'

const h = vi.hoisted(() => ({ apiGet: vi.fn() }))

vi.mock('vue-i18n', () => ({ useI18n: () => ({ t: key => key }) }))
vi.mock('@/composables/useApi', () => ({
  useApi: () => ({ apiFetch: vi.fn(), apiGet: h.apiGet }),
  resolveApiError: () => '',
}))
vi.mock('@/composables/useToast', () => ({ useToast: () => ({ showToast: vi.fn() }) }))
vi.mock('@/utils/datetime', () => ({ localizedDateTime: () => 'date' }))

import { useParamsScheduler } from '@/composables/useParamsScheduler'

const scheduler = useParamsScheduler()
const KEY = 'test-task'
const load = async seconds => {
  h.apiGet.mockResolvedValueOnce([{ key: KEY, enabled: true, interval_sec: seconds }])
  await scheduler.loadSched()
  return scheduler.schedEditValues[KEY]
}

describe('loadSched', () => {
  beforeEach(() => {
    delete scheduler.schedEditValues[KEY]
  })

  it('follows an interval changed elsewhere', async () => {
    await load(3600)
    expect(await load(7200)).toEqual({ unit: 'h', amount: 2, savedSec: 7200 })
  })

  it('leaves a value being typed', async () => {
    await load(3600)
    scheduler.schedOnAmountChange(KEY, 5)
    expect(await load(7200)).toEqual({ unit: 'h', amount: 5, savedSec: 3600 })
  })

  it('leaves the unit the admin picked when nothing changed', async () => {
    await load(3600)
    scheduler.schedOnUnitChange(KEY, 'm')
    expect(await load(3600)).toEqual({ unit: 'm', amount: 60, savedSec: 3600 })
  })
})
