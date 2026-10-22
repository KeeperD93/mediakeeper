/**
 * Statistics → Tools exclusions: a list that failed to load offers a retry
 * instead of "no exclusions", then shows the list.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

const h = vi.hoisted(() => ({ apiGet: vi.fn() }))

vi.mock('@/composables/useApi', () => ({
  useApi: () => ({ apiGet: h.apiGet, apiPost: vi.fn(), apiDelete: vi.fn() }),
  resolveApiError: code => code,
}))
vi.mock('@/composables/useToast', () => ({ useToast: () => ({ showToast: vi.fn() }) }))
vi.mock('@/composables/useStats', () => ({ useStats: () => ({ loadTotals: vi.fn() }) }))

import StatsExclusions from '@/components/stats/StatsExclusions.vue'

let wrapper
// The failed load is logged: keep it out of the test output.
let consoleError

beforeEach(() => {
  vi.clearAllMocks()
  consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
})
afterEach(() => {
  wrapper?.unmount()
  consoleError.mockRestore()
})

describe('StatsExclusions', () => {
  it('offers a retry when the list fails to load, then shows the list', async () => {
    h.apiGet
      .mockRejectedValueOnce(new TypeError('Failed to fetch'))
      .mockResolvedValueOnce([{ mode: 'exact', value: 'Sample title' }])
    wrapper = mount(StatsExclusions)
    await flushPromises()

    const empty = wrapper.find('.excl-empty')
    expect(empty.text()).toContain('stats.exclusionsLoadError')
    expect(empty.text()).not.toContain('stats.noExclusions')

    await empty.find('button').trigger('click')
    await flushPromises()
    expect(wrapper.find('.excl-empty').exists()).toBe(false)
    expect(wrapper.find('.excl-val').text()).toBe('Sample title')
  })
})
