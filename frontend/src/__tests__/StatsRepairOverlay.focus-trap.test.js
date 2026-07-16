/**
 * Covers useFocusTrap wired into StatsRepairOverlay: initial focus onto the
 * close button, Escape closing the dialog, and the "no close mid-run" guard.
 */
import { describe, it, expect, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

vi.mock('vue-i18n', () => ({
  useI18n: () => ({ t: key => key }),
}))

vi.mock('lucide-vue-next', () => ({
  RefreshCw: { name: 'RefreshCwStub', template: '<i />' },
  X: { name: 'XStub', template: '<i />' },
  ArrowRight: { name: 'ArrowRightStub', template: '<i />' },
}))

import StatsRepairOverlay from '@/components/stats/StatsRepairOverlay.vue'

const RESULT = {
  candidates: 1,
  migrated: 0,
  unresolved: 1,
  errors: 0,
  details: [
    {
      item_id: 'i2',
      item_name: 'A Movie',
      status: 'unresolved',
      fallback: 'Sub',
      ancestors: [{ type: 'Folder', name: 'Sub' }],
    },
  ],
}

function buildOverlay(props = {}) {
  return mount(StatsRepairOverlay, {
    props: { open: true, running: false, result: RESULT, error: '', ...props },
    global: { mocks: { $t: key => key } },
    attachTo: document.body,
  })
}

describe('StatsRepairOverlay — focus trap integration', () => {
  it('moves initial focus into the dialog even while running (close button disabled)', async () => {
    // Real flow: the overlay always opens with running=true, so the close button
    // is disabled — focus must land on the dialog panel, not stay outside.
    const w = buildOverlay({ running: true, result: null })
    await flushPromises()

    const panel = document.querySelector('.rlo-modal')
    expect(document.activeElement).toBe(panel)

    w.unmount()
  })

  it('routes Escape to close and emits close', async () => {
    const w = buildOverlay()
    await flushPromises()

    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))
    await flushPromises()

    expect(w.emitted('close')).toBeTruthy()

    w.unmount()
  })

  it('does not emit close on Escape while a run is in progress', async () => {
    const w = buildOverlay({ running: true, result: null })
    await flushPromises()

    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))
    await flushPromises()

    expect(w.emitted('close')).toBeFalsy()

    w.unmount()
  })
})
