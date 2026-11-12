/**
 * Leaving the page after a sign-in: the button stays busy while the page is left,
 * and is freed when the navigation does not leave it.
 */
import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

vi.mock('vue-i18n', () => ({ useI18n: () => ({ t: key => key }) }))

const pushMock = vi.fn()
const currentRoute = { value: { name: 'login' } }
vi.mock('vue-router', () => ({
  useRoute: () => ({ query: {} }),
  useRouter: () => ({ push: pushMock, replace: vi.fn(), currentRoute }),
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

const PAUSE_OVER = 1000

async function filledForm() {
  const w = mount(LoginView)
  for (let i = 0; i < 10; i++) await flushPromises()
  await w.find('input[autocomplete="username"]').setValue('someone')
  await w.find('input[autocomplete="current-password"]').setValue('not-a-real-password')
  return w
}

const submit = w => w.find('form').trigger('submit')

let consoleError

beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date'] })
  loginMock.mockReset()
  currentRoute.value = { name: 'login' }
  // A navigation leaves the page unless a test says otherwise.
  pushMock.mockReset().mockImplementation(async () => {
    currentRoute.value = { name: 'portal-home' }
  })
  consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
})

afterEach(() => {
  consoleError.mockRestore()
  vi.useRealTimers()
})

describe('LoginView — leaving the page after a sign-in', () => {
  it('sends nothing more once a sign-in succeeds, while the page is being left', async () => {
    loginMock.mockResolvedValue({ scope: 'portal' })
    const w = await filledForm()

    await submit(w)
    await flushPromises()
    vi.setSystemTime(Date.now() + PAUSE_OVER)
    await submit(w)
    await flushPromises()

    expect(loginMock).toHaveBeenCalledTimes(1)
    expect(pushMock).toHaveBeenCalledExactlyOnceWith('/portal')
    expect(w.find('button.login-submit').attributes('disabled')).toBeDefined()
  })

  it.each([
    ['fails', () => Promise.resolve(Object.assign(new Error('aborted'), { type: 4 })), false],
    ['comes back to this page', () => Promise.resolve(), false],
    ['throws', () => Promise.reject(new Error('unexpected')), true],
  ])('frees the button when the navigation after a sign-in %s', async (_, navigate, told) => {
    loginMock.mockResolvedValue({ scope: 'portal' })
    pushMock.mockImplementationOnce(navigate)
    const w = await filledForm()

    await submit(w)
    await flushPromises()
    expect(w.find('button.login-submit').attributes('disabled')).toBeUndefined()
    expect(w.find('.login-error').exists()).toBe(told)

    vi.setSystemTime(Date.now() + PAUSE_OVER)
    await submit(w)
    await flushPromises()
    expect(loginMock).toHaveBeenCalledTimes(2)
  })
})
