/**
 * Covers useFocusTrap wired into ForceUsernameModal — a *forced* dialog
 * the user cannot dismiss with Escape. The trap must move focus onto
 * the input, and Escape must NOT close or submit the modal.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

const apiGet = vi.fn()
const showToast = vi.fn()
const updateProfile = vi.fn()

vi.mock('@/composables/useApi', () => ({
  useApi: () => ({
    apiGet,
    apiPost: vi.fn(),
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

vi.mock('@/composables/portal/usePortalAuth', () => ({
  usePortalAuth: () => ({
    profile: { value: null },
    updateProfile,
  }),
}))

vi.mock('vue-i18n', () => ({
  useI18n: () => ({ t: key => key }),
}))

import ForceUsernameModal from '@/components/portal/settings/ForceUsernameModal.vue'

function buildModal(props = {}) {
  return mount(ForceUsernameModal, {
    props: { open: true, ...props },
    attachTo: document.body,
  })
}

describe('ForceUsernameModal — focus trap integration', () => {
  beforeEach(() => {
    apiGet.mockReset()
    showToast.mockReset()
    updateProfile.mockReset()
  })

  it('moves initial focus onto the username input when the dialog opens', async () => {
    const w = buildModal()
    await flushPromises()

    const input = w.get('#pt-force-uname-input').element
    expect(document.activeElement).toBe(input)

    w.unmount()
  })

  it('does NOT emit close, done or submit when Escape is pressed (forced modal)', async () => {
    const w = buildModal()
    await flushPromises()

    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))
    await flushPromises()

    expect(w.emitted('close')).toBeFalsy()
    expect(w.emitted('done')).toBeFalsy()
    expect(w.emitted('submit')).toBeFalsy()

    w.unmount()
  })

  it('opens empty when no initial pseudo is provided (back-compat)', async () => {
    const w = buildModal()
    await flushPromises()
    expect(w.get('#pt-force-uname-input').element.value).toBe('')
    w.unmount()
  })

  it('pre-fills the generated pseudo (silent account never shows an Emby login)', async () => {
    const w = buildModal({ initial: 'Renard-Bleu-42' })
    await flushPromises()
    expect(w.get('#pt-force-uname-input').element.value).toBe('Renard-Bleu-42')
    w.unmount()
  })

  it('pre-filled pseudo is savable (reason=current) and confirm keeps it', async () => {
    apiGet.mockResolvedValue({ available: true, reason: 'current' })
    updateProfile.mockResolvedValue({})

    const w = buildModal({ initial: 'Renard-Bleu-42' })
    await flushPromises()
    // Wait out the 300ms check-username debounce that arm() armed.
    await new Promise(resolve => setTimeout(resolve, 350))
    await flushPromises()
    expect(apiGet).toHaveBeenCalledWith(expect.stringContaining('Renard-Bleu-42'))

    const btn = w.get('.pt-settings-btn--primary')
    expect(btn.attributes('disabled')).toBeUndefined()

    await btn.trigger('click')
    await flushPromises()
    expect(updateProfile).toHaveBeenCalledWith({ display_name: 'Renard-Bleu-42' })
    expect(w.emitted('done')).toBeTruthy()
    w.unmount()
  })
})
