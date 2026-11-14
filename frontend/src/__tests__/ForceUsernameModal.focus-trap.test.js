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

  it('opens empty: the stored name can no longer be confirmed', async () => {
    const w = buildModal()
    await flushPromises()
    expect(w.get('#pt-force-uname-input').element.value).toBe('')
    expect(apiGet).not.toHaveBeenCalled()
    w.unmount()
  })

  async function typeAndCheck(w, value) {
    await w.get('#pt-force-uname-input').setValue(value)
    // Wait out the 300ms check-username debounce.
    await new Promise(resolve => setTimeout(resolve, 350))
    await flushPromises()
  }

  it('says why a name is refused and keeps the button off', async () => {
    apiGet.mockResolvedValue({ available: false, reason: 'generated', suggestions: [] })
    const w = buildModal()
    await flushPromises()

    await typeAndCheck(w, 'Test Owl 42')

    const flag = w.get('.pt-settings-uname-flag')
    expect(flag.text()).toBe('portal.settings.identity.usernameGenerated')
    expect(flag.classes()).toContain('pt-settings-uname-flag--err')
    expect(w.get('.pt-settings-btn--primary').attributes('disabled')).toBeDefined()
    w.unmount()
  })

  it('saves a free name, and shows the reason when the save refuses it', async () => {
    apiGet.mockResolvedValue({ available: true, reason: 'free', suggestions: [] })
    updateProfile.mockRejectedValueOnce(new Error('display_name_reserved'))
    const w = buildModal()
    await flushPromises()

    await typeAndCheck(w, 'Alice')
    await w.get('.pt-settings-btn--primary').trigger('click')
    await flushPromises()

    expect(updateProfile).toHaveBeenCalledWith({ display_name: 'Alice' })
    expect(w.get('.pt-settings-uname-flag').text()).toBe(
      'portal.settings.identity.usernameReserved',
    )
    expect(w.emitted('done')).toBeFalsy()
    w.unmount()
  })
})
