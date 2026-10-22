/**
 * Each tool card ends with its action, so the button sits at the card's
 * bottom-left; a result renders just above that button, in a region screen
 * readers announce, and the file input stays reachable with the keyboard.
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

vi.mock('vue-i18n', () => ({ useI18n: () => ({ t: k => k }) }))
vi.mock('@/composables/useApi', () => ({
  useApi: () => ({
    apiFetch: vi
      .fn()
      .mockResolvedValue({ json: async () => ({ playback_imported: 3, playback_skipped: 1 }) }),
    apiGet: vi.fn().mockResolvedValue([]),
    apiPost: vi.fn().mockResolvedValue({ total_purged: 2 }),
    apiDelete: vi.fn(),
  }),
  resolveApiError: code => code,
}))
vi.mock('@/composables/useToast', () => ({ useToast: () => ({ showToast: vi.fn() }) }))
vi.mock('@/composables/useStats', () => ({ useStats: () => ({ loadTotals: vi.fn() }) }))
vi.mock('@/composables/useConfirm', () => ({ useConfirm: () => vi.fn().mockResolvedValue(true) }))
vi.mock('@/components/stats/StatsRepairOverlay.vue', () => ({
  default: { name: 'StatsRepairOverlay', template: '<div />' },
}))

import StatsToolsTab from '@/components/stats/StatsToolsTab.vue'

let wrapper
const cards = w => w.findAll('.tools-grid > .tool-card')

afterEach(() => wrapper?.unmount())

describe('StatsToolsTab — tool card layout', () => {
  it('ends each tool card with its action', () => {
    wrapper = mount(StatsToolsTab)

    expect(cards(wrapper)).toHaveLength(3)
    for (const card of cards(wrapper)) {
      expect(card.element.lastElementChild.classList).toContain('tool-action')
    }
  })

  it('shows the import and purge results just above their buttons, announced', async () => {
    wrapper = mount(StatsToolsTab)
    const input = wrapper.find('input[type="file"]')
    Object.defineProperty(input.element, 'files', {
      value: [new File(['{}'], 'history.json', { type: 'application/json' })],
    })
    await input.trigger('change')
    await cards(wrapper)[1].find('button').trigger('click')
    await flushPromises()

    for (const card of cards(wrapper).slice(0, 2)) {
      const region = card.element.lastElementChild.previousElementSibling
      expect(region.getAttribute('role')).toBe('status')
      expect(region.querySelector('.tool-status')).not.toBeNull()
    }
  })

  it('keeps the file input reachable with the keyboard', () => {
    wrapper = mount(StatsToolsTab)
    const input = wrapper.find('input[type="file"]')

    expect(input.classes()).toContain('sr-only')
    expect(input.attributes('tabindex')).toBeUndefined()
  })
})
