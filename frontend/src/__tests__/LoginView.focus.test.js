/**
 * Where the focus goes after a refused sign-in: back on the password when the
 * press on the button left it on the page, so that Enter retries.
 */
import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

vi.mock('vue-i18n', () => ({ useI18n: () => ({ t: key => key }) }))

vi.mock('vue-router', () => ({
  useRoute: () => ({ query: {} }),
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}))

const loginMock = vi.fn()
vi.mock('@/composables/useAuth', () => ({
  useAuth: () => ({ login: loginMock, checkAuth: () => Promise.resolve(false) }),
}))

vi.mock('@/composables/signInErrors', () => ({
  signInErrorMessage: ({ message, retryAfter }) => `${message}:${retryAfter}`,
}))

vi.mock('@/composables/portal/usePortalAuth', () => ({
  usePortalAuth: () => ({ checkPortalAuth: () => Promise.resolve(false) }),
}))

vi.mock('@/composables/portal/useMaintenance', () => ({
  useMaintenance: () => ({
    fetchMaintenanceState: () => Promise.resolve({ enabled: false, text: '' }),
    refresh: () => {},
  }),
}))

vi.mock('@/composables/useApi', () => ({
  fetchApiResponse: () =>
    Promise.resolve({ status: 200, ok: true, json: () => Promise.resolve({}) }),
}))

vi.mock('@/composables/useTheme', () => ({
  useTheme: () => ({ particlesEnabled: { value: false } }),
}))

vi.mock('@/composables/useLoginParticles', () => ({
  useLoginParticles: () => {},
}))

vi.mock('@/components/icons/IconDiscord.vue', () => ({
  default: { template: '<span />' },
}))

vi.mock('@/components/common/MkSpinner.vue', () => ({
  default: { template: '<span />' },
}))

vi.mock('@/assets/styles/login-view.css', () => ({}))

import LoginView from '@/views/LoginView.vue'

const wrongPassword = () => new Error('invalid_credentials')
const NAME = 'input[autocomplete="username"]'
const PASSWORD = 'input[autocomplete="current-password"]'

// The focus only moves in a page attached to the document.
async function attachedForm() {
  const w = mount(LoginView, { attachTo: document.body })
  for (let i = 0; i < 10; i++) await flushPromises()
  await w.find(NAME).setValue('someone')
  await w.find(PASSWORD).setValue('not-a-real-password')
  return w
}

const submit = w => w.find('form').trigger('submit')

let consoleError
let w

beforeEach(() => {
  loginMock.mockReset()
  consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
})

afterEach(() => {
  w.unmount()
  consoleError.mockRestore()
})

describe('LoginView — the focus after a refusal', () => {
  it.each([
    ['the button', 'button.login-submit'],
    ['the main area', 'main'],
    ['the page', null],
  ])('puts it on the password when %s had it', async (_, selector) => {
    loginMock.mockRejectedValueOnce(wrongPassword())
    w = await attachedForm()
    const start = selector ? w.find(selector).element : document.body
    if (selector) start.focus()
    else document.activeElement.blur()
    expect(document.activeElement).toBe(start)

    await submit(w)
    await flushPromises()

    expect(document.activeElement).toBe(w.find(PASSWORD).element)
    expect(w.find('.login-error').attributes('role')).toBe('alert')
  })

  it('leaves it on a field the user went to while waiting', async () => {
    let refuse
    loginMock.mockReturnValueOnce(
      new Promise((_, reject) => {
        refuse = reject
      }),
    )
    w = await attachedForm()
    w.find('button.login-submit').element.focus()

    await submit(w)
    w.find(NAME).element.focus()
    refuse(wrongPassword())
    await flushPromises()

    expect(document.activeElement).toBe(w.find(NAME).element)
  })
})
