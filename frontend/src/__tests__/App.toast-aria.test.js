import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { ref } from 'vue'

vi.mock('vue-i18n', () => ({
  useI18n: () => ({ t: key => key, locale: ref('fr') }),
}))

vi.mock('vue-router', () => ({
  useRoute: () => ({ fullPath: '/', meta: {}, name: 'home', query: {} }),
  useRouter: () => ({ currentRoute: ref({ value: { name: 'home' } }) }),
}))

vi.mock('@/composables/useApi', () => ({
  fetchApiResponse: vi.fn().mockResolvedValue({ ok: true }),
}))

const toasts = ref([])
vi.mock('@/composables/useToast', () => ({
  useToast: () => ({
    toasts,
    removeToast: vi.fn(id => {
      toasts.value = toasts.value.filter(t => t.id !== id)
    }),
  }),
}))

vi.mock('@/components/common/MkConfirmDialog.vue', () => ({
  default: { template: '<div class="mk-confirm-stub" />' },
}))

const { default: App } = await import('@/App.vue')

const baseToast = (overrides = {}) => ({
  id: 1,
  message: 'Hello',
  type: 'ok',
  module: 'Test',
  meta: null,
  ...overrides,
})

describe('App.vue — toast ARIA live region (WCAG 2.2 SC 4.1.3)', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    toasts.value = []
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('renders the toast container as a polite live region', () => {
    toasts.value = [baseToast()]
    const wrapper = mount(App)
    const container = wrapper.find('.mk-toast-container')
    expect(container.exists()).toBe(true)
    expect(container.attributes('role')).toBe('region')
    expect(container.attributes('aria-live')).toBe('polite')
    expect(container.attributes('aria-atomic')).toBe('false')
    expect(container.attributes('aria-label')).toBeTruthy()
    wrapper.unmount()
  })

  it('marks "ok" toasts with role="status" and no per-toast aria-live override', () => {
    toasts.value = [baseToast({ id: 10, type: 'ok' })]
    const wrapper = mount(App)
    const toast = wrapper.find('.mk-toast.ok')
    expect(toast.exists()).toBe(true)
    expect(toast.attributes('role')).toBe('status')
    expect(toast.attributes('aria-live')).toBeUndefined()
    wrapper.unmount()
  })

  it('marks "err" toasts with role="alert" and aria-live="assertive"', () => {
    toasts.value = [baseToast({ id: 20, type: 'err', message: 'Boom' })]
    const wrapper = mount(App)
    const toast = wrapper.find('.mk-toast.err')
    expect(toast.exists()).toBe(true)
    expect(toast.attributes('role')).toBe('alert')
    expect(toast.attributes('aria-live')).toBe('assertive')
    wrapper.unmount()
  })
})
