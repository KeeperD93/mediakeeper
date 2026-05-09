/**
 * Covers useFocusTrap wired into PortalWhatsNewModal: initial focus on
 * the close button and Escape routing through dismiss.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

const apiGet = vi.fn()
const apiPost = vi.fn()
const routerPush = vi.fn()

vi.mock('@/composables/useApi', () => ({
  useApi: () => ({
    apiGet,
    apiPost,
    apiPut: vi.fn(),
    apiDelete: vi.fn(),
    apiPatch: vi.fn(),
    apiFetch: vi.fn(),
    loading: { value: false },
    error: { value: null },
  }),
}))

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: routerPush }),
}))

vi.mock('vue-i18n', () => ({
  useI18n: () => ({ t: key => key, locale: { value: 'fr' } }),
}))

vi.mock('lucide-vue-next', () => ({
  Lightbulb: { name: 'LightbulbStub', template: '<i />' },
  X: { name: 'XStub', template: '<i />' },
}))

import PortalWhatsNewModal from '@/components/portal/PortalWhatsNewModal.vue'

function buildModal(props = {}) {
  return mount(PortalWhatsNewModal, {
    props: { auto: false, open: false, ...props },
    attachTo: document.body,
  })
}

describe('PortalWhatsNewModal — focus trap integration', () => {
  beforeEach(() => {
    apiGet.mockReset()
    apiPost.mockReset()
    routerPush.mockReset()
    apiGet.mockResolvedValue({
      versions: [{ version: '1.0.0', categories: { added: ['feature x'] } }],
    })
    apiPost.mockResolvedValue({ version: '1.0.0' })
  })

  it('moves initial focus onto the close button when the dialog opens', async () => {
    const w = buildModal()
    await w.setProps({ open: true })
    await flushPromises()
    await flushPromises()

    const closeBtn = document.querySelector('.dwn-close')
    expect(closeBtn).not.toBeNull()
    expect(document.activeElement).toBe(closeBtn)

    w.unmount()
  })

  it('routes Escape to dismiss and emits close exactly once', async () => {
    const w = buildModal()
    await w.setProps({ open: true })
    await flushPromises()
    await flushPromises()

    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))
    await flushPromises()

    expect(w.emitted('close')).toBeTruthy()
    expect(w.emitted('close').length).toBe(1)

    w.unmount()
  })
})
