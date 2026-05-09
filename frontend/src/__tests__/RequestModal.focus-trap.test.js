/**
 * Covers the useFocusTrap composable wired into RequestModal: initial
 * focus, Escape, and Tab wrap-around inside the dialog.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

const apiGet = vi.fn()
const apiPost = vi.fn()
const showToast = vi.fn()

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

vi.mock('@/composables/useToast', () => ({
  useToast: () => ({ showToast }),
}))

vi.mock('vue-i18n', () => ({
  useI18n: () => ({ t: key => key }),
}))

vi.mock('lucide-vue-next', () => ({
  X: { name: 'XStub', template: '<i />' },
}))

import RequestModal from '@/components/portal/RequestModal.vue'

const movieItem = {
  id: 27205,
  tmdb_id: 27205,
  title: 'Inception',
  year: 2010,
  media_type: 'movie',
  poster_url: '',
  backdrop_url: '',
}

function buildModal(props = {}) {
  return mount(RequestModal, {
    props: { item: movieItem, isAdmin: false, ...props },
    attachTo: document.body,
  })
}

describe('RequestModal — focus trap integration', () => {
  beforeEach(() => {
    apiGet.mockReset()
    apiPost.mockReset()
    showToast.mockReset()
    apiGet.mockResolvedValue(null)
    apiPost.mockImplementation(() => new Promise(() => {}))
  })

  it('moves initial focus onto the close button when the dialog opens', async () => {
    const w = buildModal()
    await flushPromises()

    const closeBtn = w.get('.pt-rmodal-close').element
    expect(document.activeElement).toBe(closeBtn)

    w.unmount()
  })

  it('routes Escape to requestClose and emits close', async () => {
    const w = buildModal()
    await flushPromises()

    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))
    await flushPromises()

    expect(w.emitted('close')).toBeTruthy()
    expect(w.emitted('close').length).toBe(1)

    w.unmount()
  })

  it('wraps Tab from the submit button back to the close button', async () => {
    const w = buildModal()
    await flushPromises()

    const closeBtn = w.get('.pt-rmodal-close').element
    const submitBtn = w.get('.pt-rmodal-btn').element

    submitBtn.focus()
    expect(document.activeElement).toBe(submitBtn)

    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Tab', bubbles: true }))
    expect(document.activeElement).toBe(closeBtn)

    w.unmount()
  })
})
