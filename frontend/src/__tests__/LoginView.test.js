import { describe, it, expect, vi, beforeAll } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

beforeAll(() => {
  const proto = globalThis.HTMLImageElement?.prototype
  if (proto && !Object.getOwnPropertyDescriptor(proto, 'src')?.set?.__patched) {
    const setter = function () {
      /* no-op: avoid jsdom resource fetch on file:/// paths */
    }
    setter.__patched = true
    Object.defineProperty(proto, 'src', {
      configurable: true,
      get() {
        return this.getAttribute('src') || ''
      },
      set: setter,
    })
  }
})

vi.mock('vue-i18n', () => ({
  useI18n: () => ({
    t: key => key,
  }),
}))

const routeQuery = { value: {} }
vi.mock('vue-router', () => ({
  useRoute: () => ({
    get query() {
      return routeQuery.value
    },
  }),
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}))

vi.mock('@/composables/useAuth', () => ({
  useAuth: () => ({
    login: vi.fn(),
    checkAuth: vi.fn().mockResolvedValue(false),
  }),
}))

vi.mock('@/composables/portal/usePortalAuth', () => ({
  usePortalAuth: () => ({
    checkPortalAuth: vi.fn().mockResolvedValue(false),
  }),
}))

vi.mock('@/composables/useApi', () => ({
  fetchApiResponse: vi.fn().mockImplementation(url => {
    if (url === '/api/health') return Promise.resolve({ status: 200, ok: true })
    if (url === '/api/changelog/current') {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ version: '0.9.9' }),
      })
    }
    return Promise.resolve({ status: 200, ok: true, json: () => Promise.resolve({}) })
  }),
  resolveApiError: vi.fn(),
}))

vi.mock('@/composables/useTheme', () => ({
  useTheme: () => ({ particlesEnabled: { value: false } }),
}))

vi.mock('@/composables/useLoginParticles', () => ({
  initLoginParticles: () => () => {},
}))

vi.mock('@/components/icons/IconDiscord.vue', () => ({
  default: { template: '<span class="stub-discord" />' },
}))

vi.mock('@/components/common/MkSpinner.vue', () => ({
  default: { template: '<span class="stub-spinner" />' },
}))

vi.mock('@/assets/styles/login-view.css', () => ({}))

import LoginView from '@/views/LoginView.vue'

const ImgStub = {
  inheritAttrs: false,
  template: '<img :src="$attrs.src" :alt="$attrs.alt" />',
}

describe('LoginView', () => {
  it('renders exactly one github link, pointing to the canonical KeeperD93/mediakeeper repo', async () => {
    routeQuery.value = {}
    const w = mount(LoginView, {
      global: { stubs: { img: ImgStub } },
    })
    for (let i = 0; i < 10; i++) await flushPromises()
    const link = w.find('[data-test="login-github-link"]')
    expect(link.exists()).toBe(true)
    expect(link.attributes('href')).toBe('https://github.com/KeeperD93/mediakeeper')
    expect(link.attributes('rel')).toContain('noopener')
    const allGithubLinks = w.findAll('a[href*="github.com"]')
    expect(allGithubLinks).toHaveLength(1)
  })

  it('uses generic login.* keys without a portal redirect', async () => {
    routeQuery.value = {}
    const w = mount(LoginView, {
      global: { stubs: { img: ImgStub } },
    })
    for (let i = 0; i < 10; i++) await flushPromises()
    expect(w.find('h1.sr-only').text()).toBe('login.title')
    expect(w.find('.login-hero-sub').text()).toBe('login.title')
    expect(w.find('.login-submit').text()).toContain('login.submit')
  })

  it('switches to portalLogin.* keys when redirect targets /portal', async () => {
    routeQuery.value = { redirect: '/portal' }
    const w = mount(LoginView, {
      global: { stubs: { img: ImgStub } },
    })
    for (let i = 0; i < 10; i++) await flushPromises()
    expect(w.find('h1.sr-only').text()).toBe('portalLogin.title')
    expect(w.find('.login-hero-sub').text()).toBe('portalLogin.subtitle')
    expect(w.find('.login-submit').text()).toContain('portalLogin.submit')
  })

  it('treats non-string or unrelated redirects as generic login', async () => {
    routeQuery.value = { redirect: ['/portal'] }
    const w1 = mount(LoginView, {
      global: { stubs: { img: ImgStub } },
    })
    for (let i = 0; i < 10; i++) await flushPromises()
    expect(w1.find('h1.sr-only').text()).toBe('login.title')

    routeQuery.value = { redirect: '/dashboard' }
    const w2 = mount(LoginView, {
      global: { stubs: { img: ImgStub } },
    })
    for (let i = 0; i < 10; i++) await flushPromises()
    expect(w2.find('h1.sr-only').text()).toBe('login.title')
  })
})
