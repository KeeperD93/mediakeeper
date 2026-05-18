import { describe, it, expect, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { nextTick } from 'vue'

const patchIdentity = vi.fn()
const resetDisplayName = vi.fn()
const confirmMock = vi.fn()

vi.mock('vue-i18n', () => ({
  useI18n: () => ({ t: (k, p) => (p ? `${k}:${JSON.stringify(p)}` : k), te: () => false }),
}))

vi.mock('@/composables/portal/usePortalAdminUsers', () => ({
  usePortalAdminUsers: () => ({ patchIdentity, resetDisplayName }),
}))

vi.mock('@/composables/useToast', () => ({
  useToast: () => ({ showToast: vi.fn() }),
}))

vi.mock('@/composables/useConfirm', () => ({
  useConfirm: () => confirmMock,
}))

import RuTabIdentity from '@/components/portal/admin/users/tabs/RuTabIdentity.vue'

function mkUser(over = {}) {
  return {
    id: 42,
    username: 'jdoe',
    display_name: 'Jane',
    first_name: 'Jane',
    last_name: 'Doe',
    email: 'jane@example.com',
    source: 'local',
    ...over,
  }
}

describe('RuTabIdentity', () => {
  function inputByMaxlength(w, max) {
    return w.findAll('input').find(i => i.attributes('maxlength') === String(max))
  }

  it('rehydrates the form when the user prop changes after emit("changed")', async () => {
    const w = mount(RuTabIdentity, { props: { user: mkUser() } })

    const displayInput = inputByMaxlength(w, 50)
    const firstNameInput = w.findAll('input[maxlength="100"]')[0]
    expect(displayInput.element.value).toBe('Jane')
    expect(firstNameInput.element.value).toBe('Jane')

    await displayInput.setValue('Janet')
    expect(displayInput.element.value).toBe('Janet')

    await w.setProps({ user: mkUser({ display_name: 'Janet', first_name: 'JanetUpdated' }) })
    await nextTick()
    expect(displayInput.element.value).toBe('Janet')
    expect(firstNameInput.element.value).toBe('JanetUpdated')
  })

  it('hydrates the form from the PATCH response so the displayed value is the persisted one', async () => {
    patchIdentity.mockResolvedValue({
      ok: true,
      changed: { display_name: 'Janet' },
      user: mkUser({ display_name: 'Janet' }),
    })
    const w = mount(RuTabIdentity, { props: { user: mkUser() } })

    const displayInput = inputByMaxlength(w, 50)
    await displayInput.setValue('  Janet  ')

    await w.find('form').trigger('submit.prevent')
    await flushPromises()

    expect(patchIdentity).toHaveBeenCalledWith(
      42,
      expect.objectContaining({ display_name: 'Janet' }),
    )
    expect(displayInput.element.value).toBe('Janet')
    expect(w.emitted('changed')).toBeTruthy()
  })

  it('arms the display-name reset and emits changed when the admin confirms', async () => {
    confirmMock.mockResolvedValueOnce(true)
    resetDisplayName.mockResolvedValueOnce({ ok: true })
    const w = mount(RuTabIdentity, { props: { user: mkUser() } })

    const resetBtn = w
      .findAll('button[type="button"]')
      .find(b => b.text().includes('displayNameResetAction'))
    expect(resetBtn?.exists()).toBe(true)
    await resetBtn.trigger('click')
    await flushPromises()

    expect(confirmMock).toHaveBeenCalled()
    expect(resetDisplayName).toHaveBeenCalledWith(42)
    expect(w.emitted('changed')).toBeTruthy()
  })

  it('does not call the API when the admin cancels the confirm dialog', async () => {
    confirmMock.mockResolvedValueOnce(false)
    resetDisplayName.mockClear()
    const w = mount(RuTabIdentity, { props: { user: mkUser() } })

    const resetBtn = w
      .findAll('button[type="button"]')
      .find(b => b.text().includes('displayNameResetAction'))
    await resetBtn.trigger('click')
    await flushPromises()

    expect(confirmMock).toHaveBeenCalled()
    expect(resetDisplayName).not.toHaveBeenCalled()
  })

  it('disables the reset button when the flag is already set', () => {
    const w = mount(RuTabIdentity, {
      props: { user: mkUser({ display_name_must_set: true }) },
    })
    const resetBtn = w
      .findAll('button[type="button"]')
      .find(b => b.text().includes('displayNameResetAction'))
    expect(resetBtn.attributes('disabled')).toBeDefined()
  })
})
