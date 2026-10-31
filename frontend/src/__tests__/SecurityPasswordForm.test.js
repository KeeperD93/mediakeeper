/**
 * Password change in Settings > Security: a success empties the form and
 * replaces it, so password managers see the change end; a refusal names the
 * server's reason, else says the save failed; every try asks for a reload of
 * the attempts.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'
import { TOAST_TYPE } from '@/constants/toast'

const mocks = vi.hoisted(() => ({ changePassword: vi.fn(), showToast: vi.fn() }))
const MESSAGES = vi.hoisted(() => ({
  'common.apiError.current_password_invalid': 'Wrong current password.',
  'common.apiError.saveFailed': 'Save failed.',
}))

vi.mock('@/i18n', () => ({ default: { global: { t: key => MESSAGES[key] ?? key } } }))
vi.mock('vue-i18n', () => ({ useI18n: () => ({ t: key => key }) }))
vi.mock('@/composables/useAuth', () => ({
  useAuth: () => ({ user: ref({ username: 'admin' }), changePassword: mocks.changePassword }),
}))
vi.mock('@/composables/useToast', () => ({ useToast: () => ({ showToast: mocks.showToast }) }))

import SecurityPasswordForm from '@/components/settings/security/SecurityPasswordForm.vue'

const NEW_PASSWORD = 'Synthetic-Pass-2026!'

async function fill(w, current = 'Old-Synthetic-1!', next = NEW_PASSWORD, confirm = NEW_PASSWORD) {
  const fields = w.findAll('input[type="password"]')
  await fields[0].setValue(current)
  await fields[1].setValue(next)
  await fields[2].setValue(confirm)
}

describe('SecurityPasswordForm', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.spyOn(console, 'error').mockImplementation(() => {})
  })

  it('names the account for password managers', () => {
    const w = mount(SecurityPasswordForm)
    const username = w.get('input[autocomplete="username"]')
    expect(username.element.value).toBe('admin')
    expect(username.attributes('hidden')).toBeDefined()
  })

  it('keeps the button disabled until the new password is long enough', async () => {
    const w = mount(SecurityPasswordForm)
    await fill(w, 'Old-Synthetic-1!', 'Short-1!', 'Short-1!')
    expect(w.get('button[type="submit"]').attributes('disabled')).toBeDefined()

    await fill(w)
    expect(w.get('button[type="submit"]').attributes('disabled')).toBeUndefined()
  })

  it('empties and replaces the form after a change', async () => {
    mocks.changePassword.mockResolvedValue({ success: true })
    const w = mount(SecurityPasswordForm)
    await fill(w)
    const before = w.get('form').element

    await w.get('form').trigger('submit')
    await flushPromises()

    expect(mocks.changePassword).toHaveBeenCalledWith('Old-Synthetic-1!', NEW_PASSWORD)
    expect(mocks.showToast).toHaveBeenCalledWith('forcePassword.success', TOAST_TYPE.OK)
    expect(w.get('form').element).not.toBe(before)
    expect(w.findAll('input[type="password"]').map(i => i.element.value)).toEqual(['', '', ''])
    expect(w.emitted('attempted')).toHaveLength(1)
  })

  it('names a refusal, or says the save failed, and still asks for a reload', async () => {
    const w = mount(SecurityPasswordForm)
    mocks.changePassword.mockRejectedValueOnce(new Error('current_password_invalid'))
    await fill(w)
    await w.get('form').trigger('submit')
    await flushPromises()
    mocks.changePassword.mockRejectedValueOnce(new TypeError('Failed to fetch'))
    await w.get('form').trigger('submit')
    await flushPromises()

    expect(mocks.showToast.mock.calls).toEqual([
      ['Wrong current password.', TOAST_TYPE.ERR],
      ['Save failed.', TOAST_TYPE.ERR],
    ])
    expect(w.emitted('attempted')).toHaveLength(2)
  })

  it('says when the two new passwords differ, without sending anything', async () => {
    const w = mount(SecurityPasswordForm)
    await fill(w, 'Old-Synthetic-1!', NEW_PASSWORD, 'Synthetic-Pass-2027!')
    await w.get('form').trigger('submit')

    expect(mocks.changePassword).not.toHaveBeenCalled()
    expect(mocks.showToast).toHaveBeenCalledWith('forcePassword.mismatch', TOAST_TYPE.ERR)
  })
})
