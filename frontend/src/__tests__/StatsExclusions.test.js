/**
 * Statistics → Tools exclusions: both fields are named for screen readers, a
 * list that failed to load offers a retry instead of "no exclusions", then
 * shows the list, and a row's remove button names that row's entry.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

const h = vi.hoisted(() => ({ apiGet: vi.fn(), apiFetch: vi.fn() }))

vi.mock('@/composables/useApi', () => ({
  useApi: () => ({ apiGet: h.apiGet, apiPost: vi.fn(), apiFetch: h.apiFetch }),
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
  it('names the match type menu and the title field for screen readers', async () => {
    h.apiGet.mockResolvedValueOnce([])
    wrapper = mount(StatsExclusions)
    await flushPromises()

    expect(wrapper.find('select.excl-sel').attributes('aria-label')).toBe(
      'stats.exclusionModeLabel',
    )
    expect(wrapper.find('input.excl-input').attributes('aria-label')).toBe(
      'stats.exclusionTitleLabel',
    )
  })

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

  it('removes the entry of the clicked row by its mode and title', async () => {
    const second = { mode: 'contains', value: 'Trailer' }
    h.apiGet.mockResolvedValueOnce([{ mode: 'exact', value: 'Sample title' }, second])
    h.apiFetch.mockResolvedValueOnce({ json: async () => [] })
    wrapper = mount(StatsExclusions)
    await flushPromises()

    await wrapper.findAll('.excl-item button').at(1).trigger('click')
    await flushPromises()
    expect(h.apiFetch).toHaveBeenCalledWith('/api/stats/exclusions', {
      method: 'DELETE',
      body: JSON.stringify(second),
    })
  })
})
