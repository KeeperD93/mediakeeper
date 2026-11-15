/**
 * First-login wizard inside the real portal page: the real layout, the real wizard and
 * the real profile store, only the HTTP faked. The last save replaces the profile, which
 * takes the wizard away: « What's new today? » must still open, chained, right after.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import i18n from '@/i18n'
import PortalDailyDigestOverlay from '@/components/portal/PortalDailyDigestOverlay.vue'
import PortalLayout from '@/components/portal/PortalLayout.vue'
import PortalOnboardingWizard from '@/components/portal/wizard/PortalOnboardingWizard.vue'
import { usePortalAuth } from '@/composables/portal/usePortalAuth'
import {
  api,
  member,
  next,
  resetBench,
  serverAnswers,
  typeName,
  walkTo,
} from './_onboardingWizardHarness'

const { authMe, route } = vi.hoisted(() => ({
  authMe: vi.fn(),
  route: { name: 'portal-home' },
}))

vi.mock('vue-router', () => ({
  useRoute: () => route,
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}))
// The HTTP layer alone: the profile store above it is the real one.
vi.mock('@/composables/useApi', async () => {
  const { ref } = await import('vue')
  const { api } = await import('./_onboardingWizardSpies')
  return {
    useApi: () => ({ ...api, loading: ref(false), error: ref(null) }),
    fetchApiResponse: authMe,
  }
})
vi.mock('@/composables/portal/usePortalLocale', () => ({
  usePortalLocale: () => ({ applyPortalLocale: vi.fn(), restoreGlobalLocale: vi.fn() }),
}))
vi.mock('@/composables/portal/usePortalChat', () => ({
  usePortalChat: () => ({ initGlobalChat: vi.fn(), shutdownGlobalChat: vi.fn() }),
}))

// Everything around the wizard and the digest stays out of the way.
const AROUND = [
  'RouterView',
  'PortalNav',
  'PortalBottomNav',
  'HomeFab',
  'SurpriseOverlay',
  'DeletionPendingBanner',
  'EventBanner',
  'PortalHelpOverlay',
  'PortalDailyDigestOverlay',
]
const SAVED = { display_name: 'Bruno', display_name_must_set: false, onboarding_pending: false }
const wrappers = []

/** Open the portal as `profile`, loaded by `/auth/me` as on a real visit. */
async function visit(profile) {
  authMe.mockResolvedValue({ ok: true, status: 200, json: async () => ({ profile }) })
  const wrapper = mount(PortalLayout, {
    attachTo: document.body,
    global: {
      plugins: [i18n],
      mocks: { $t: i18n.global.t },
      stubs: Object.fromEntries(AROUND.map(name => [name, true])),
    },
  })
  wrappers.push(wrapper)
  await flushPromises()
  return wrapper
}

const wizard = wrapper => wrapper.findComponent(PortalOnboardingWizard)
const digest = wrapper => wrapper.findComponent(PortalDailyDigestOverlay)

beforeEach(() => {
  resetBench()
  usePortalAuth().clearPortalAuth()
  serverAnswers({ verdicts: { Bruno: { reason: 'free', available: true } } })
  vi.useFakeTimers()
})
afterEach(() => {
  wrappers.splice(0).forEach(wrapper => wrapper.unmount())
  vi.useRealTimers()
})

describe('PortalOnboardingWizard in the portal page, its end', () => {
  it('hands the whole tour over to « What’s new today? », chained', async () => {
    api.apiPost.mockResolvedValue(member(SAVED))
    const wrapper = await visit(
      member({ display_name: 'Renard-Bleu-42', display_name_must_set: true }),
    )
    expect(wizard(wrapper).exists()).toBe(true)
    expect(digest(wrapper).exists()).toBe(false)

    await next(wrapper)
    await typeName(wrapper, 'Bruno')
    await walkTo(wrapper, 'C’est parti, Bruno !')
    await next(wrapper)

    expect(usePortalAuth().profile.value.onboarding_pending).toBe(false)
    expect(wizard(wrapper).exists()).toBe(false)
    expect(digest(wrapper).props()).toMatchObject({ open: true, chained: true, auto: false })
  })

  it('hands a name reset over to « What’s new today? », chained', async () => {
    api.apiPut.mockResolvedValue(member(SAVED))
    const wrapper = await visit(
      member({ display_name: 'Alice_42', display_name_must_set: true, onboarding_pending: false }),
    )

    await typeName(wrapper, 'Bruno')
    await next(wrapper)

    expect(usePortalAuth().profile.value.display_name).toBe('Bruno')
    expect(wizard(wrapper).exists()).toBe(false)
    expect(digest(wrapper).props()).toMatchObject({ open: true, chained: true, auto: false })
  })
})
