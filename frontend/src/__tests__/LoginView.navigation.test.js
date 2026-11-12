/**
 * Leaving the page after a sign-in, under the real router: the button stays busy
 * while the page is left, and is freed when the navigation does not leave it.
 */
import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory, RouterView } from 'vue-router'

vi.mock('vue-i18n', () => ({ useI18n: () => ({ t: key => key }) }))

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
const ADMIN = { scope: 'admin', must_change_password: false }
const PENDING_ADMIN = { scope: 'admin', must_change_password: true }
const MEMBER = { scope: 'portal' }

// A test can hold a route behind a gate: its guard answers what the gate returns.
const gates = {}
const landing = name => ({
  path: name === 'home' ? '/' : `/${name}`,
  name,
  component: { template: `<p>${name}</p>` },
  beforeEnter: () => gates[name]?.() ?? true,
})

let router
let w

async function signInPage(query = {}) {
  router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/login', name: 'login', component: LoginView },
      landing('home'),
      landing('portal'),
    ],
  })
  router.push({ path: '/login', query })
  await router.isReady()
  w = mount(RouterView, { global: { plugins: [router] } })
  for (let i = 0; i < 10; i++) await flushPromises()
  await w.find('input[autocomplete="username"]').setValue('Alice')
  await w.find('input[autocomplete="current-password"]').setValue('not-a-real-password')
}

async function submit() {
  await w.find('form').trigger('submit')
  await flushPromises()
}

const button = () => w.find('button.login-submit')

// A navigation still running until the test lets it through.
function holdRoute(name) {
  let open
  const held = new Promise(resolve => {
    open = resolve
  })
  gates[name] = () => held
  return () => open(true)
}

// Any navigation from now on throws, as when the next page's files are gone.
function breakNavigation() {
  router.beforeEach(() => {
    throw new Error('unexpected')
  })
}

function stubLocation() {
  const location = { origin: 'http://localhost', assign: vi.fn() }
  vi.stubGlobal('location', location)
  return location
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date'] })
  loginMock.mockReset()
  for (const name of Object.keys(gates)) delete gates[name]
  vi.spyOn(console, 'error').mockImplementation(() => {})
  vi.spyOn(console, 'warn').mockImplementation(() => {})
})

afterEach(() => {
  w.unmount()
  vi.useRealTimers()
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
})

describe('LoginView — leaving the page after a sign-in', () => {
  it.each([
    ['an admin', ADMIN, 'home'],
    ['an admin with a temporary password', PENDING_ADMIN, 'home'],
    ['a member', MEMBER, 'portal'],
  ])('keeps the button busy while %s leaves the page', async (_, signedIn, destination) => {
    const letThrough = holdRoute(destination)
    loginMock.mockResolvedValue(signedIn)
    await signInPage()

    await submit()
    expect(button().attributes('disabled')).toBeDefined()
    vi.setSystemTime(Date.now() + PAUSE_OVER)
    await submit()
    expect(loginMock).toHaveBeenCalledTimes(1)

    letThrough()
    await flushPromises()
    expect(router.currentRoute.value.name).toBe(destination)
  })

  it.each([
    ['is stopped by a guard', () => false],
    ['is sent back to this page', () => ({ name: 'login', query: { redirect: '/portal' } })],
  ])('frees the button when the navigation after a sign-in %s', async (_, guard) => {
    gates.portal = guard
    loginMock.mockResolvedValue(MEMBER)
    await signInPage()

    await submit()
    expect(router.currentRoute.value.name).toBe('login')
    expect(button().attributes('disabled')).toBeUndefined()
    expect(w.find('.login-error').exists()).toBe(false)

    delete gates.portal
    vi.setSystemTime(Date.now() + PAUSE_OVER)
    await submit()
    expect(loginMock).toHaveBeenCalledTimes(2)
    expect(router.currentRoute.value.name).toBe('portal')
  })

  it.each([
    ['an admin', ADMIN, 'http://localhost/'],
    [
      'an admin with a temporary password',
      PENDING_ADMIN,
      'http://localhost/?force_change_password=1',
    ],
    ['a member', MEMBER, 'http://localhost/portal'],
  ])('loads the next page in full when the navigation of %s throws', async (_, signedIn, url) => {
    loginMock.mockResolvedValue(signedIn)
    await signInPage()
    const location = stubLocation()
    breakNavigation()

    await submit()

    expect(location.assign).toHaveBeenCalledExactlyOnceWith(url)
    expect(w.find('.login-error').exists()).toBe(false)
    expect(button().attributes('disabled')).toBeDefined()
  })

  it.each(['//elsewhere.example/page', '/\\elsewhere.example/page'])(
    'keeps that full load on this site when the redirect is %s',
    async redirect => {
      loginMock.mockResolvedValue(ADMIN)
      await signInPage({ redirect })
      const location = stubLocation()
      breakNavigation()

      await submit()

      expect(location.assign).toHaveBeenCalledExactlyOnceWith('/')
    },
  )
})
