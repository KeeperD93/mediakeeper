/**
 * Covers RequestModal dialog semantics, Escape handling, submit guard,
 * and initial focus.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'

const apiGet = vi.fn()
const apiPost = vi.fn()
const showToast = vi.fn()
const profileRef = ref(null)

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

vi.mock('@/composables/portal/usePortalAuth', () => ({
  usePortalAuth: () => ({ profile: profileRef }),
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

describe('RequestModal — a11y & keyboard', () => {
  beforeEach(() => {
    apiGet.mockReset()
    apiPost.mockReset()
    showToast.mockReset()
    apiGet.mockResolvedValue(null)
    // Default to a never-resolving submit so submitting stays true once
    // a test triggers the submit button. Tests that need a successful
    // submit can override this in-place.
    apiPost.mockImplementation(() => new Promise(() => {}))
  })

  it('renders an accessible dialog with role, aria-modal and aria-labelledby tied to the h2', async () => {
    const w = buildModal()
    await flushPromises()

    const panel = w.get('.pt-rmodal')
    expect(panel.attributes('role')).toBe('dialog')
    expect(panel.attributes('aria-modal')).toBe('true')

    const labelledBy = panel.attributes('aria-labelledby')
    expect(labelledBy).toBeTruthy()

    const title = w.get(`#${labelledBy}`)
    expect(title.element.tagName.toLowerCase()).toBe('h2')

    w.unmount()
  })

  it('emits close on Escape when not submitting', async () => {
    const w = buildModal()
    await flushPromises()

    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
    await flushPromises()

    expect(w.emitted('close')).toBeTruthy()
    expect(w.emitted('close').length).toBe(1)

    w.unmount()
  })

  it('does not emit close on Escape while submitting', async () => {
    const w = buildModal()
    await flushPromises()

    // Trigger submit → ``submitting`` becomes true synchronously, then
    // the function awaits the never-resolving apiPost mock so the guard
    // window stays open for the assertion below.
    await w.get('.pt-rmodal-btn').trigger('click')
    expect(apiPost).toHaveBeenCalled()

    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
    await flushPromises()

    expect(w.emitted('close')).toBeFalsy()

    w.unmount()
  })

  it('moves initial focus to the close button after mount', async () => {
    const w = buildModal()
    await flushPromises()

    const closeBtn = w.get('.pt-rmodal-close')
    expect(document.activeElement).toBe(closeBtn.element)

    w.unmount()
  })
})

describe('RequestModal — admin on-behalf-of default', () => {
  const users = [
    { user_id: 1, display_name: 'Alice' },
    { user_id: 42, display_name: 'Bob (admin)' },
    { user_id: 3, display_name: 'Charlie' },
  ]

  beforeEach(() => {
    apiGet.mockReset()
    apiPost.mockReset()
    showToast.mockReset()
    apiPost.mockImplementation(() => new Promise(() => {}))
    apiGet.mockImplementation(url =>
      url.includes('/admin/users') ? Promise.resolve({ items: users }) : Promise.resolve(null),
    )
    profileRef.value = null
  })

  function selectedOption(w) {
    return w.findAll('.pt-input option').find(o => o.element.selected)
  }

  it('defaults the picker to the logged-in admin, not the first user alphabetically', async () => {
    profileRef.value = { user_id: 42, role: 'admin' }
    const w = buildModal({ isAdmin: true })
    await flushPromises()

    expect(selectedOption(w)?.text()).toContain('Bob')

    w.unmount()
  })

  it('falls back to the first user when the admin is absent from the list', async () => {
    profileRef.value = { user_id: 999, role: 'admin' }
    const w = buildModal({ isAdmin: true })
    await flushPromises()

    expect(selectedOption(w)?.text()).toContain('Alice')

    w.unmount()
  })
})
