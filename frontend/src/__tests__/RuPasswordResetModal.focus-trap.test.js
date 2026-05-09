/**
 * Covers useFocusTrap wired into RuPasswordResetModal: initial focus on
 * the close button and Escape routing through the close handler.
 */
import { describe, it, expect, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

vi.mock('vue-i18n', () => ({
  useI18n: () => ({ t: key => key }),
}))

vi.mock('lucide-vue-next', () => ({
  Check: { name: 'CheckStub', template: '<i />' },
  Copy: { name: 'CopyStub', template: '<i />' },
  X: { name: 'XStub', template: '<i />' },
}))

import RuPasswordResetModal from '@/components/portal/admin/users/RuPasswordResetModal.vue'

function buildModal(props = {}) {
  return mount(RuPasswordResetModal, {
    props: { open: true, password: 'testpwd', ...props },
    attachTo: document.body,
  })
}

describe('RuPasswordResetModal — focus trap integration', () => {
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
