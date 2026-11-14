import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, shallowMount } from '@vue/test-utils'
import { nextTick, ref } from 'vue'

import PortalDailyDigestOverlay from '@/components/portal/PortalDailyDigestOverlay.vue'
import PortalLayout from '@/components/portal/PortalLayout.vue'
import PortalNav from '@/components/portal/PortalNav.vue'
import PortalOnboardingWizard from '@/components/portal/wizard/PortalOnboardingWizard.vue'
import { USER_ROLE } from '@/constants/auth'
import { WIZARD_MODE } from '@/constants/portalOnboarding'

const profile = ref(null)
const ui = ref({})
const route = { name: 'portal-home' }
const checkPortalAuth = vi.fn().mockResolvedValue(true)
const apiGet = vi.fn()

vi.mock('vue-router', () => ({
  useRoute: () => route,
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}))
vi.mock('vue-i18n', async importOriginal => ({
  ...(await importOriginal()),
  useI18n: () => ({ locale: ref('fr'), t: key => key }),
}))
vi.mock('@/composables/useApi', () => ({ useApi: () => ({ apiGet, apiPost: vi.fn() }) }))
vi.mock('@/composables/portal/usePortalAuth', () => ({
  usePortalAuth: () => ({ profile, ui, checkPortalAuth }),
}))
vi.mock('@/composables/portal/usePortalNews', () => ({
  usePortalNews: () => ({ markRead: vi.fn() }),
}))
vi.mock('@/composables/portal/usePortalLocale', () => ({
  usePortalLocale: () => ({ applyPortalLocale: vi.fn(), restoreGlobalLocale: vi.fn() }),
}))
vi.mock('@/composables/portal/usePortalChat', () => ({
  usePortalChat: () => ({ initGlobalChat: vi.fn(), shutdownGlobalChat: vi.fn() }),
}))

function player(overrides = {}) {
  return {
    id: 5,
    user_id: 5,
    role: 'viewer',
    display_name: 'Alice',
    display_name_must_set: false,
    onboarding_pending: false,
    ...overrides,
  }
}

// A layout left mounted reacts to the next test's profile: each one goes at the end of its test.
const mounted = []
afterEach(() => {
  mounted.splice(0).forEach(wrapper => wrapper.unmount())
  route.name = 'portal-home'
})

async function visit(initial, stubs = {}) {
  profile.value = initial
  const wrapper = shallowMount(PortalLayout, {
    global: { stubs: { RouterView: true, ...stubs } },
  })
  mounted.push(wrapper)
  await flushPromises()
  return wrapper
}

// The wizard's last save: the server clears its flags, then the wizard hands over.
async function finishWizard(wrapper) {
  profile.value = { ...profile.value, onboarding_pending: false, display_name_must_set: false }
  wrapper.findComponent(PortalOnboardingWizard).vm.$emit('done')
  await nextTick()
}

const wizard = wrapper => wrapper.findComponent(PortalOnboardingWizard)
const digest = wrapper => wrapper.findComponent(PortalDailyDigestOverlay)

describe('PortalLayout.vue, the first-login wizard', () => {
  it('opens the whole tour while it is due, and nothing else', async () => {
    const wrapper = await visit(player({ onboarding_pending: true }))

    expect(wizard(wrapper).props('mode')).toBe(WIZARD_MODE.FULL)
    expect(digest(wrapper).exists()).toBe(false)
  })

  it('opens the name alone after an admin reset it', async () => {
    const wrapper = await visit(player({ display_name_must_set: true }))

    expect(wizard(wrapper).props('mode')).toBe(WIZARD_MODE.RESET)
    expect(digest(wrapper).exists()).toBe(false)
  })

  it('shows the tour to an admin once, but never the reset', async () => {
    const tour = await visit(player({ role: USER_ROLE.ADMIN, onboarding_pending: true }))
    expect(wizard(tour).props('mode')).toBe(WIZARD_MODE.FULL)

    const reset = await visit(player({ role: USER_ROLE.ADMIN, display_name_must_set: true }))
    expect(wizard(reset).exists()).toBe(false)
  })

  it('keeps the tour for when the portal opens again, not the name reset', async () => {
    route.name = 'portal-maintenance'
    const tour = await visit(player({ onboarding_pending: true }))
    expect(wizard(tour).exists()).toBe(false)

    const reset = await visit(player({ display_name_must_set: true }))
    expect(wizard(reset).exists()).toBe(true)
  })

  it.each([
    ['the tour', { onboarding_pending: true }],
    ['the name reset', { display_name_must_set: true }],
  ])('hands over to the digest, at once and in its frame, after %s', async (_, flags) => {
    const wrapper = await visit(player(flags))

    await finishWizard(wrapper)

    expect(wizard(wrapper).exists()).toBe(false)
    expect(digest(wrapper).props()).toMatchObject({ open: true, chained: true, auto: false })
  })

  it('opens the digest the next time from the avatar menu as usual', async () => {
    const wrapper = await visit(player({ onboarding_pending: true }))
    await finishWizard(wrapper)

    digest(wrapper).vm.$emit('close')
    await nextTick()
    expect(digest(wrapper).props()).toMatchObject({ open: false, chained: false })

    wrapper.findComponent(PortalNav).vm.$emit('open-daily-digest')
    await nextTick()
    expect(digest(wrapper).props()).toMatchObject({ open: true, chained: false })
  })
})

describe('PortalLayout.vue, the window that opens by itself', () => {
  it('opens on a visit without the wizard', async () => {
    const wrapper = await visit(player())

    expect(digest(wrapper).props('auto')).toBe(true)
    expect(wizard(wrapper).exists()).toBe(false)
  })

  it('opens again by itself on the next portal load', async () => {
    const first = await visit(player({ onboarding_pending: true }))
    await finishWizard(first)
    mounted.splice(mounted.indexOf(first), 1)
    first.unmount()

    const next = await visit(player())

    expect(digest(next).props()).toMatchObject({ auto: true, open: false })
  })
})

describe('PortalLayout.vue, with the real daily digest', () => {
  const DIGEST_AUTO = '/api/portal/daily-digest'
  const DIGEST_MANUAL = '/api/portal/daily-digest?force=true'

  const visitWithRealDigest = initial => visit(initial, { PortalDailyDigestOverlay: false })

  const urls = () => apiGet.mock.calls.map(([url]) => url)

  beforeEach(() => {
    apiGet.mockReset().mockResolvedValue({ digest: null })
  })

  it('checks for content on a visit without the wizard, and nothing else', async () => {
    await visitWithRealDigest(player())

    // The news and the new version live in the digest: no window of their own asks the server.
    expect(urls()).toEqual([DIGEST_AUTO])
  })

  it('asks nothing while the wizard is open', async () => {
    await visitWithRealDigest(player({ onboarding_pending: true }))

    expect(urls()).toEqual([])
  })

  it('loads it fresh, once, as soon as the wizard ends', async () => {
    const wrapper = await visitWithRealDigest(player({ onboarding_pending: true }))

    await finishWizard(wrapper)
    await flushPromises()

    // Fresh: the digest of the hour may still carry the name from before.
    expect(urls()).toEqual([DIGEST_MANUAL])
  })
})
