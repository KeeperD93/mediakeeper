/**
 * Covers useFocusTrap wired into RuBulkPermsModal (the unified bulk-edit
 * overlay): initial focus on the close button and Escape routing through the
 * close handler. Mirrors the sibling modal focus-trap suites (§23.6).
 */
import { describe, it, expect, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

vi.mock('lucide-vue-next', () => ({
  X: { name: 'XStub', template: '<i />' },
}))

import RuBulkPermsModal from '@/components/portal/admin/users/RuBulkPermsModal.vue'

function buildModal(props = {}) {
  return mount(RuBulkPermsModal, {
    props: { open: true, count: 3, ...props },
    global: { mocks: { $t: key => key } },
    attachTo: document.body,
  })
}

describe('RuBulkPermsModal — focus trap integration', () => {
  it('moves initial focus onto the close button when the dialog opens', async () => {
    const w = buildModal()
    await flushPromises()

    const closeBtn = w.get('.atl-close').element
    expect(document.activeElement).toBe(closeBtn)

    w.unmount()
  })

  it('routes Escape to the close handler and emits close exactly once', async () => {
    const w = buildModal()
    await flushPromises()

    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))
    await flushPromises()

    expect(w.emitted('close')).toBeTruthy()
    expect(w.emitted('close').length).toBe(1)

    w.unmount()
  })
})
