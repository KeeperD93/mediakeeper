/**
 * Signing in from the page: the form the browser and password managers see, the
 * refusal it shows, and one try at a time whatever the Enter key does.
 */
import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

vi.mock('vue-i18n', () => ({ useI18n: () => ({ t: key => key }) }))

const pushMock = vi.fn()
vi.mock('vue-router', () => ({
  useRoute: () => ({ query: {} }),
  useRouter: () => ({ push: pushMock, replace: vi.fn() }),
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
const PAUSE_OVER = 1000
const NAME = 'input[autocomplete="username"]'
const PASSWORD = 'input[autocomplete="current-password"]'

async function mountPage() {
  const w = mount(LoginView)
  for (let i = 0; i < 10; i++) await flushPromises()
  return w
}

async function filledForm() {
  const w = await mountPage()
  await w.find(NAME).setValue('someone')
  await w.find(PASSWORD).setValue('not-a-real-password')
  return w
}

// What a real browser fires on Enter in a field or a press of the button; the
// test DOM fires neither, the e2e specs cover that part.
const submit = w => w.find('form').trigger('submit')

function keydownEnter(element, { repeat = false } = {}) {
  const event = new KeyboardEvent('keydown', {
    key: 'Enter',
    repeat,
    bubbles: true,
    cancelable: true,
  })
  element.dispatchEvent(event)
  return event
}

let consoleError

beforeEach(() => {
  loginMock.mockReset()
  pushMock.mockReset()
  consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
})

afterEach(() => {
  consoleError.mockRestore()
})

describe('LoginView — the form browsers fill', () => {
  it('names the saved-login fields and keeps them in one form with its button', async () => {
    const w = await mountPage()
    const form = w.find('form').element
    const name = w.find(NAME)
    const password = w.find(PASSWORD)
    const button = w.find('button.login-submit')

    expect(name.attributes('type')).toBe('text')
    expect(password.attributes('type')).toBe('password')
    expect(button.attributes('type')).toBe('submit')
    for (const control of [name, password, w.find('.login-checkbox'), button]) {
      expect(control.element.form).toBe(form)
    }
  })

  it('ties each label to its field', async () => {
    const w = await mountPage()
    const targets = w
      .findAll('label.login-label')
      .map(label => w.find(`[id="${label.attributes('for')}"]`).attributes('autocomplete'))

    expect(targets).toEqual(['username', 'current-password'])
  })

  it('gives the fields no name, so no native submission can carry them', async () => {
    const w = await mountPage()

    expect(w.find(NAME).attributes('name')).toBeUndefined()
    expect(w.find(PASSWORD).attributes('name')).toBeUndefined()
  })

  it('cancels the native submission of the form', async () => {
    const w = await filledForm()
    loginMock.mockRejectedValueOnce(wrongPassword())
    const event = new Event('submit', { bubbles: true, cancelable: true })

    w.find('form').element.dispatchEvent(event)
    await flushPromises()

    expect(event.defaultPrevented).toBe(true)
    expect(loginMock).toHaveBeenCalledTimes(1)
  })
})

describe('LoginView — signing in', () => {
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ['Date'] })
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('shows a refused sign-in with its wait in the page, as an alert', async () => {
    const refusal = Object.assign(new Error('login_rate_limited'), { retryAfter: 42 })
    loginMock.mockRejectedValueOnce(refusal)
    const w = await filledForm()

    await submit(w)
    await flushPromises()

    const error = w.find('.login-error')
    expect(error.attributes('role')).toBe('alert')
    expect(error.text()).toBe('login_rate_limited:42')
    expect(consoleError).toHaveBeenCalledWith('[LoginView.doLogin]', refusal)
  })

  it('sends one try when the form is submitted', async () => {
    loginMock.mockRejectedValue(wrongPassword())
    const w = await filledForm()

    await submit(w)
    await flushPromises()

    expect(loginMock).toHaveBeenCalledExactlyOnceWith('someone', 'not-a-real-password')
  })

  it('ignores a submission while a sign-in is running, then listens again', async () => {
    let refuse
    loginMock.mockReturnValueOnce(
      new Promise((_, reject) => {
        refuse = reject
      }),
    )
    const w = await filledForm()

    await submit(w)
    await submit(w)
    expect(loginMock).toHaveBeenCalledTimes(1)

    refuse(wrongPassword())
    await flushPromises()
    vi.setSystemTime(Date.now() + PAUSE_OVER)
    loginMock.mockRejectedValueOnce(wrongPassword())
    await submit(w)
    await flushPromises()

    expect(loginMock).toHaveBeenCalledTimes(2)
  })

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

  it('counts a second press right after a refusal as the same try', async () => {
    loginMock.mockRejectedValue(wrongPassword())
    const w = await filledForm()

    await submit(w)
    await flushPromises()
    vi.setSystemTime(Date.now() + PAUSE_OVER - 2)
    await submit(w)
    await flushPromises()
    expect(loginMock).toHaveBeenCalledTimes(1)

    vi.setSystemTime(Date.now() + 2)
    await submit(w)
    await flushPromises()
    expect(loginMock).toHaveBeenCalledTimes(2)
  })

  it.each([NAME, PASSWORD, '.login-checkbox', 'button.login-submit'])(
    'cancels a held Enter on %s, never the first press',
    async selector => {
      const w = await filledForm()
      const element = w.find(selector).element

      expect(keydownEnter(element).defaultPrevented).toBe(false)
      expect(keydownEnter(element, { repeat: true }).defaultPrevented).toBe(true)
    },
  )

  it('does not hold back a first try, nor one after a form left incomplete', async () => {
    loginMock.mockRejectedValue(wrongPassword())
    const w = await filledForm()

    await w.find(PASSWORD).setValue('')
    await submit(w)
    expect(w.find('.login-error').text()).toBe('login.allRequired')
    expect(loginMock).not.toHaveBeenCalled()

    await w.find(PASSWORD).setValue('not-a-real-password')
    await submit(w)
    await flushPromises()
    expect(loginMock).toHaveBeenCalledTimes(1)
  })
})
