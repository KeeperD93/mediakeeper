/**
 * Signing in from the page: the refusal it shows, and one try at a time whatever
 * the Enter key does.
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
  initLoginParticles: () => () => {},
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
const PAUSE_OVER = 1000

async function filledForm() {
  const w = mount(LoginView)
  for (let i = 0; i < 10; i++) await flushPromises()
  await w.find('input[type="text"]').setValue('someone')
  await w.find('input[type="password"]').setValue('not-a-real-password')
  return w
}

describe('LoginView — signing in', () => {
  let consoleError

  beforeEach(() => {
    loginMock.mockReset()
    consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
    vi.useFakeTimers({ toFake: ['Date'] })
  })

  afterEach(() => {
    consoleError.mockRestore()
    vi.useRealTimers()
  })

  it('shows a refused sign-in with its wait in the page, as an alert', async () => {
    const refusal = Object.assign(new Error('login_rate_limited'), { retryAfter: 42 })
    loginMock.mockRejectedValueOnce(refusal)
    const w = await filledForm()

    await w.find('button.login-submit').trigger('click')
    await flushPromises()

    const error = w.find('.login-error')
    expect(error.attributes('role')).toBe('alert')
    expect(error.text()).toBe('login_rate_limited:42')
    expect(consoleError).toHaveBeenCalledWith('[LoginView.doLogin]', refusal)
  })

  it.each(['input[type="text"]', 'input[type="password"]'])(
    'sends one try with Enter in %s',
    async field => {
      loginMock.mockRejectedValue(wrongPassword())
      const w = await filledForm()

      await w.find(field).trigger('keydown', { key: 'Enter' })
      await flushPromises()

      expect(loginMock).toHaveBeenCalledTimes(1)
    },
  )

  it('ignores Enter while a sign-in is running, then listens again', async () => {
    let refuse
    loginMock.mockReturnValueOnce(
      new Promise((_, reject) => {
        refuse = reject
      }),
    )
    const w = await filledForm()
    const field = w.find('input[type="password"]')

    await field.trigger('keydown', { key: 'Enter' })
    await field.trigger('keydown', { key: 'Enter' })
    await w.find('input[type="text"]').trigger('keydown', { key: 'Enter' })
    expect(loginMock).toHaveBeenCalledTimes(1)

    refuse(wrongPassword())
    await flushPromises()
    vi.setSystemTime(Date.now() + PAUSE_OVER)
    loginMock.mockRejectedValueOnce(wrongPassword())
    await field.trigger('keydown', { key: 'Enter' })
    await flushPromises()

    expect(loginMock).toHaveBeenCalledTimes(2)
  })

  it.each([
    ['Enter', w => w.find('input[type="password"]').trigger('keydown', { key: 'Enter' })],
    ['the button', w => w.find('button.login-submit').trigger('click')],
  ])('counts a second press of %s right after a refusal as the same try', async (_, press) => {
    loginMock.mockRejectedValue(wrongPassword())
    const w = await filledForm()

    await press(w)
    await flushPromises()
    vi.setSystemTime(Date.now() + PAUSE_OVER - 2)
    await press(w)
    await flushPromises()
    expect(loginMock).toHaveBeenCalledTimes(1)

    vi.setSystemTime(Date.now() + 2)
    await press(w)
    await flushPromises()
    expect(loginMock).toHaveBeenCalledTimes(2)
  })

  it('does not hold back a first try, nor one after a form left incomplete', async () => {
    loginMock.mockRejectedValue(wrongPassword())
    const w = await filledForm()
    const password = w.find('input[type="password"]')

    await password.setValue('')
    await password.trigger('keydown', { key: 'Enter' })
    expect(w.find('.login-error').text()).toBe('login.allRequired')
    expect(loginMock).not.toHaveBeenCalled()

    await password.setValue('not-a-real-password')
    await password.trigger('keydown', { key: 'Enter' })
    await flushPromises()
    expect(loginMock).toHaveBeenCalledTimes(1)
  })

  it('does not count a held Enter as new tries, however long it is held', async () => {
    loginMock.mockRejectedValue(wrongPassword())
    const w = await filledForm()
    const field = w.find('input[type="password"]')

    await field.trigger('keydown', { key: 'Enter' })
    await flushPromises()
    vi.setSystemTime(Date.now() + PAUSE_OVER)
    await field.trigger('keydown', { key: 'Enter', repeat: true })
    await field.trigger('keydown', { key: 'Enter', repeat: true })
    await flushPromises()

    expect(loginMock).toHaveBeenCalledTimes(1)
  })
})
