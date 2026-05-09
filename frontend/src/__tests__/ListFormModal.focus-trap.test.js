/**
 * Covers useFocusTrap wired into ListFormModal: initial focus on the
 * close button and Escape routing through the close handler.
 */
import { describe, it, expect, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

vi.mock('vue-i18n', () => ({
  useI18n: () => ({ t: key => key }),
}))

vi.mock('lucide-vue-next', () => ({
  X: { name: 'XStub', template: '<i />' },
}))

import ListFormModal from '@/components/portal/lists/ListFormModal.vue'

function buildModal(props = {}) {
  return mount(ListFormModal, {
    props: { open: true, mode: 'create', ...props },
    attachTo: document.body,
  })
}

describe('ListFormModal — focus trap integration', () => {
  it('moves initial focus onto the close button when the dialog opens', async () => {
    const w = buildModal()
    await flushPromises()

    const closeBtn = w.get('.lfm-close').element
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
