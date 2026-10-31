/**
 * The forced password change shows a readable reason when the change fails,
 * and nothing of its own over a rate limit, whose toast already says it.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

const h = vi.hoisted(() => ({
  changePassword: vi.fn(),
  showToast: vi.fn(),
  // What resolveApiError gives: a known code its message, a rate limit nothing.
  messages: {
    current_password_invalid: 'message:current_password_invalid',
    rate_limited_notified: '',
  },
}))

vi.mock('vue-i18n', () => ({ useI18n: () => ({ t: k => k }) }))
vi.mock('@/composables/useAuth', () => ({ useAuth: () => ({ changePassword: h.changePassword }) }))
vi.mock('@/composables/useToast', () => ({ useToast: () => ({ showToast: h.showToast }) }))
vi.mock('@/composables/useApi', () => ({
  resolveApiError: (code, fallbackKey) => h.messages[code] ?? fallbackKey,
}))

import ForcePasswordModal from '@/components/ForcePasswordModal.vue'

const NEW_PASSWORD = 'A-new-passw0rd-for-tests'

async function changeFails(code) {
  h.changePassword.mockRejectedValueOnce(new Error(code))
  const w = mount(ForcePasswordModal)
  const [current, next, confirm] = w.findAll('input[type="password"]')
  await current.setValue('the-old-one')
  await next.setValue(NEW_PASSWORD)
  await confirm.setValue(NEW_PASSWORD)
  await w.find('button').trigger('click')
  await flushPromises()
  return w.find('.text-red-300')
}

describe('ForcePasswordModal — a failed change', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.spyOn(console, 'error').mockImplementation(() => {})
  })

  it("shows the server's reason and logs the error", async () => {
    expect((await changeFails('current_password_invalid')).text()).toBe(
      'message:current_password_invalid',
    )
    expect(console.error).toHaveBeenCalledWith('[ForcePasswordModal.submit]', expect.any(Error))
  })

  it('names the failed action for an unknown answer', async () => {
    expect((await changeFails('http_502')).text()).toBe('common.apiError.saveFailed')
  })

  it('adds nothing to the rate-limit toast', async () => {
    expect((await changeFails('rate_limited_notified')).exists()).toBe(false)
    expect(h.showToast).not.toHaveBeenCalled()
  })
})
