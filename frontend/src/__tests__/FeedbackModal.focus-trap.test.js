/**
 * Covers useFocusTrap wired into FeedbackModal: initial focus on the close
 * button, Escape routed through the close handler, and no Escape close while
 * a report is being sent.
 */
import { describe, it, expect, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

const h = vi.hoisted(() => ({ apiPost: vi.fn() }))

vi.mock('vue-i18n', () => ({ useI18n: () => ({ t: k => k }) }))
vi.mock('vue-router', () => ({
  useRoute: () => ({ name: 'stats', query: {} }),
  useRouter: () => ({ push: vi.fn() }),
}))
vi.mock('@/composables/useToast', () => ({ useToast: () => ({ showToast: vi.fn() }) }))
vi.mock('@/composables/useApi', () => ({
  useApi: () => ({ apiPost: h.apiPost }),
  resolveApiError: code => code,
}))

import FeedbackModal from '@/components/feedback/FeedbackModal.vue'

async function buildModal() {
  const w = mount(FeedbackModal, { props: { open: false }, attachTo: document.body })
  await w.setProps({ open: true })
  await flushPromises()
  return w
}

const pressEscape = () =>
  document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))

describe('FeedbackModal — focus trap integration', () => {
  it('moves initial focus onto the close button when the dialog opens', async () => {
    const w = await buildModal()
    expect(document.activeElement).toBe(w.get('.fbk-close').element)
    w.unmount()
  })

  it('routes Escape to the close handler and emits close exactly once', async () => {
    const w = await buildModal()
    pressEscape()
    await flushPromises()
    expect(w.emitted('close')).toHaveLength(1)
    w.unmount()
  })

  it('ignores Escape while a report is being sent', async () => {
    let finishSend
    h.apiPost.mockImplementationOnce(() => new Promise(resolve => (finishSend = resolve)))
    const w = await buildModal()
    await w.get('input[type="text"]').setValue('Sample title')
    await w.get('textarea').setValue('Sample description')
    await w.get('form').trigger('submit')

    pressEscape()
    await flushPromises()
    expect(w.emitted('close')).toBeUndefined()

    finishSend({ ok: true })
    await flushPromises()
    expect(w.emitted('close')).toHaveLength(1) // closed by the send, not by Escape
    w.unmount()
  })
})
