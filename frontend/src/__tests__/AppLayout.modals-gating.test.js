import { describe, it, expect, vi } from 'vitest'
import { shallowMount } from '@vue/test-utils'
import { ref } from 'vue'

vi.mock('@/i18n', () => ({ getLocale: () => 'fr' }))

vi.mock('vue-i18n', () => ({
  useI18n: () => ({ t: key => key, locale: ref('fr') }),
}))

vi.mock('vue-router', () => ({
  useRoute: () => ({ fullPath: '/', meta: {}, name: 'home', query: {} }),
  useRouter: () => ({
    currentRoute: ref({ value: { name: 'home' } }),
    push: vi.fn().mockResolvedValue(undefined),
  }),
  RouterView: { template: '<div class="router-view-stub" />' },
}))

vi.mock('@/composables/useApi', () => ({
  fetchApiResponse: vi.fn().mockResolvedValue({ ok: true, json: async () => ({}) }),
  useApi: () => ({
    apiGet: vi.fn().mockResolvedValue({}),
    apiFetch: vi.fn().mockResolvedValue({}),
  }),
}))

const mustChangePassword = ref(false)
vi.mock('@/composables/useAuth', () => ({
  useAuth: () => ({
    mustChangePassword,
    startTokenRefresh: vi.fn(),
  }),
}))

vi.mock('@/composables/useTheme', () => ({
  useTheme: () => ({ syncFromServer: vi.fn() }),
}))

vi.mock('@/composables/useKonamiCode', () => ({
  useKonamiCode: vi.fn(),
}))

vi.mock('@/composables/useToast', () => ({
  useToast: () => ({ showToast: vi.fn(), toasts: ref([]), removeToast: vi.fn() }),
}))

const stubs = {
  AppSidebar: { template: '<div class="sidebar-stub" />' },
  AppTopbar: { template: '<div class="topbar-stub" />' },
  DeploymentBanner: { template: '<div class="deployment-banner-stub" />' },
  SearchModal: { template: '<div class="search-modal-stub" />' },
  ForcePasswordModal: { template: '<div class="force-password-stub" />' },
  OnboardingWizard: { template: '<div class="onboarding-wizard-stub" />' },
  WhatsNewModal: { template: '<div class="whatsnew-stub" />' },
  // `router-view` is auto-registered by vue-router in production; the
  // module is mocked here, so we stub the element explicitly.
  'router-view': { template: '<div class="router-view-stub" />' },
}

const { default: AppLayout } = await import('@/components/layout/AppLayout.vue')

describe('AppLayout — modals gating around mustChangePassword', () => {
  it('hides the OnboardingWizard while mustChangePassword is true', async () => {
    mustChangePassword.value = true
    const wrapper = shallowMount(AppLayout, { global: { stubs } })
    expect(wrapper.find('.force-password-stub').exists()).toBe(true)
    expect(wrapper.find('.onboarding-wizard-stub').exists()).toBe(false)
    wrapper.unmount()
  })

  it('renders the OnboardingWizard once mustChangePassword has cleared', async () => {
    mustChangePassword.value = false
    const wrapper = shallowMount(AppLayout, { global: { stubs } })
    expect(wrapper.find('.force-password-stub').exists()).toBe(false)
    expect(wrapper.find('.onboarding-wizard-stub').exists()).toBe(true)
    wrapper.unmount()
  })
})
