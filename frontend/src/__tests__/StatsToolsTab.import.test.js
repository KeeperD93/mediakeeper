/**
 * Statistics → Tools tab wiring: a failed history import shows its reason in
 * the card (a rate limit leaves no empty strip, its own toast says it), and
 * the picked file is cleared only once the import ends.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

const h = vi.hoisted(() => ({ apiFetch: vi.fn(), apiGet: vi.fn(), showToast: vi.fn() }))

vi.mock('vue-i18n', () => ({ useI18n: () => ({ t: k => k }) }))
vi.mock('@/composables/useApi', () => ({
  useApi: () => ({
    apiFetch: h.apiFetch,
    apiGet: h.apiGet,
    apiPost: vi.fn(),
    apiDelete: vi.fn(),
  }),
  // A rate limit resolves to nothing; any other code to its message.
  resolveApiError: code => (code === 'rate_limited_notified' ? '' : `message:${code}`),
}))
vi.mock('@/composables/useToast', () => ({ useToast: () => ({ showToast: h.showToast }) }))
vi.mock('@/composables/useStats', () => ({ useStats: () => ({ loadTotals: vi.fn() }) }))
vi.mock('@/composables/useConfirm', () => ({ useConfirm: () => vi.fn() }))
vi.mock('@/components/stats/StatsRepairOverlay.vue', () => ({
  default: { name: 'StatsRepairOverlay', template: '<div />' },
}))

import StatsToolsTab from '@/components/stats/StatsToolsTab.vue'

let wrapper
// Each failure is logged: keep the expected ones out of the test output.
let consoleError

beforeEach(() => {
  vi.clearAllMocks()
  h.apiGet.mockResolvedValue([])
  consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
})
afterEach(() => {
  wrapper?.unmount()
  consoleError.mockRestore()
})

async function importFails(code) {
  h.apiFetch.mockRejectedValueOnce(new Error(code))
  wrapper = mount(StatsToolsTab)
  const input = wrapper.find('input[type="file"]')
  Object.defineProperty(input.element, 'files', {
    value: [new File(['{}'], 'history.json', { type: 'application/json' })],
  })
  await input.trigger('change')
  await flushPromises()
  return wrapper.findAll('.tool-status')
}

describe('StatsToolsTab — import failure', () => {
  it('shows the reason in the import status', async () => {
    const status = await importFails('file_too_large')

    expect(status).toHaveLength(1)
    expect(status[0].classes()).toContain('err')
    expect(status[0].text()).toBe('message:file_too_large')
  })

  it('leaves no empty error strip over a rate limit', async () => {
    expect(await importFails('rate_limited_notified')).toHaveLength(0)
  })
})

describe('StatsToolsTab — file input', () => {
  it('clears the picked file only once the import ends', async () => {
    let finish
    h.apiFetch.mockReturnValueOnce(
      new Promise(resolve => {
        finish = resolve
      }),
    )
    wrapper = mount(StatsToolsTab)
    const input = wrapper.find('input[type="file"]')
    const setValue = vi.fn()
    Object.defineProperty(input.element, 'files', { value: [new File(['{}'], 'history.json')] })
    Object.defineProperty(input.element, 'value', { set: setValue })
    await input.trigger('change')
    expect(setValue).not.toHaveBeenCalled()

    finish(null)
    await flushPromises()
    expect(setValue).toHaveBeenCalledWith('')
  })
})
