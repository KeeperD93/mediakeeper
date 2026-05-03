import { describe, it, expect, vi, beforeEach, beforeAll } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

beforeAll(() => {
  const proto = globalThis.HTMLImageElement?.prototype
  if (proto && !Object.getOwnPropertyDescriptor(proto, 'src')?.set?.__patched) {
    const setter = function () { /* no-op: avoid jsdom resource fetch on file:/// paths */ }
    setter.__patched = true
    Object.defineProperty(proto, 'src', {
      configurable: true,
      get() { return this.getAttribute('src') || '' },
      set: setter,
    })
  }
})

vi.mock('vue-i18n', () => ({
  useI18n: () => ({
    t: (key) => key,
  }),
}))

vi.mock('vue-router', () => ({
  useRoute: () => ({ query: {} }),
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
  fetchApiResponse: vi.fn().mockImplementation((url) => {
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
  it('renders the github source code link in the login footer once the backend is ready', async () => {
    const w = mount(LoginView, {
      global: { stubs: { img: ImgStub } },
    })
    for (let i = 0; i < 10; i++) await flushPromises()
    const link = w.find('[data-test="login-github-link"]')
    expect(link.exists()).toBe(true)
    expect(link.attributes('href')).toBe('https://github.com/KeeperD93/mediakeeper')
    expect(link.attributes('rel')).toContain('noopener')
    expect(link.text()).toContain('attribution.githubLink')
  })
})
