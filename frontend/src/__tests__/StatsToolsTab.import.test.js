/**
 * A failed history import shows its reason under the button; a rate limit
 * leaves no empty error strip there, its own toast says it.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

const h = vi.hoisted(() => ({ apiFetch: vi.fn() }))

vi.mock('vue-i18n', () => ({ useI18n: () => ({ t: k => k }) }))
vi.mock('@/composables/useApi', () => ({
  useApi: () => ({
    apiFetch: h.apiFetch,
    apiGet: vi.fn().mockResolvedValue([]),
    apiPost: vi.fn(),
    apiDelete: vi.fn(),
  }),
  // A rate limit resolves to nothing; any other code to its message.
  resolveApiError: code => (code === 'rate_limited_notified' ? '' : `message:${code}`),
}))
vi.mock('@/composables/useStats', () => ({ useStats: () => ({ loadTotals: vi.fn() }) }))
vi.mock('@/composables/useConfirm', () => ({ useConfirm: () => vi.fn() }))
vi.mock('@/components/stats/StatsRepairOverlay.vue', () => ({
  default: { name: 'StatsRepairOverlay', template: '<div />' },
}))

import StatsToolsTab from '@/components/stats/StatsToolsTab.vue'

async function importFails(code) {
  h.apiFetch.mockRejectedValueOnce(new Error(code))
  const w = mount(StatsToolsTab)
  const input = w.find('input[type="file"]')
  Object.defineProperty(input.element, 'files', {
    value: [new File(['{}'], 'history.json', { type: 'application/json' })],
  })
  await input.trigger('change')
  await flushPromises()
  return w.findAll('.tool-status')
}

describe('StatsToolsTab — import failure', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.spyOn(console, 'error').mockImplementation(() => {})
  })

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
