import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, shallowMount } from '@vue/test-utils'
import { nextTick, ref } from 'vue'

import PortalDailyDigestOverlay from '@/components/portal/PortalDailyDigestOverlay.vue'
import PortalLayout from '@/components/portal/PortalLayout.vue'
import PortalNav from '@/components/portal/PortalNav.vue'
import ForceUsernameModal from '@/components/portal/settings/ForceUsernameModal.vue'
import { USER_ROLE } from '@/constants/auth'

const profile = ref(null)
const ui = ref({})
const checkPortalAuth = vi.fn().mockResolvedValue(true)
const apiGet = vi.fn()

vi.mock('vue-router', () => ({
  useRoute: () => ({ name: 'portal-home' }),
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
    ...overrides,
  }
}

// A layout left mounted reacts to the next test's profile: each one goes at the end of its test.
const mounted = []
afterEach(() => mounted.splice(0).forEach(wrapper => wrapper.unmount()))

async function visit(initial, stubs = {}) {
  profile.value = initial
  const wrapper = shallowMount(PortalLayout, {
    global: { stubs: { RouterView: true, ...stubs } },
  })
  mounted.push(wrapper)
  await flushPromises()
  return wrapper
}

async function setMustPick(value) {
  profile.value = { ...profile.value, display_name_must_set: value }
  await nextTick()
}

const digestOpensByItself = wrapper => wrapper.findComponent(PortalDailyDigestOverlay).props('auto')

describe('PortalLayout.vue, the window that opens by itself', () => {
  it('opens on a visit without the username picker', async () => {
    const wrapper = await visit(player())

    expect(digestOpensByItself(wrapper)).toBe(true)
    expect(wrapper.findComponent(ForceUsernameModal).exists()).toBe(false)
  })

  it('shows only the picker while a username is owed', async () => {
    const wrapper = await visit(player({ display_name_must_set: true }))

    expect(wrapper.findComponent(ForceUsernameModal).exists()).toBe(true)
    expect(wrapper.findComponent(PortalDailyDigestOverlay).exists()).toBe(false)
  })

  it('opens nothing by itself once the username is saved', async () => {
    const wrapper = await visit(player({ display_name_must_set: true }))

    await setMustPick(false)

    expect(wrapper.findComponent(ForceUsernameModal).exists()).toBe(false)
    expect(digestOpensByItself(wrapper)).toBe(false)
  })

  it('keeps the avatar menu working after the picker', async () => {
    const wrapper = await visit(player({ display_name_must_set: true }))
    await setMustPick(false)

    wrapper.findComponent(PortalNav).vm.$emit('open-daily-digest')
    await nextTick()

    expect(wrapper.findComponent(PortalDailyDigestOverlay).props('open')).toBe(true)
  })

  it('opens again on the next portal load', async () => {
    const first = await visit(player({ display_name_must_set: true }))
    await setMustPick(false)
    mounted.splice(mounted.indexOf(first), 1)
    first.unmount()

    const next = await visit(player())

    expect(digestOpensByItself(next)).toBe(true)
  })

  it('applies to a name reset during the visit', async () => {
    const wrapper = await visit(player())
    expect(digestOpensByItself(wrapper)).toBe(true)

    await setMustPick(true)
    await setMustPick(false)

    expect(digestOpensByItself(wrapper)).toBe(false)
  })

  it('does not hold it back for an admin', async () => {
    const wrapper = await visit(player({ role: USER_ROLE.ADMIN, display_name_must_set: true }))

    expect(wrapper.findComponent(ForceUsernameModal).exists()).toBe(false)
    expect(digestOpensByItself(wrapper)).toBe(true)
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

  it('checks for content on a visit without the picker, and nothing else', async () => {
    await visitWithRealDigest(player())

    // The news and the new version live in the digest: no window of their own asks the server.
    expect(urls()).toEqual([DIGEST_AUTO])
  })

  it('checks for nothing once the username is saved', async () => {
    await visitWithRealDigest(player({ display_name_must_set: true }))

    await setMustPick(false)
    await flushPromises()

    expect(urls()).toEqual([])
  })

  it('loads it on demand from the avatar menu after the picker', async () => {
    const wrapper = await visitWithRealDigest(player({ display_name_must_set: true }))
    await setMustPick(false)
    await flushPromises()

    wrapper.findComponent(PortalNav).vm.$emit('open-daily-digest')
    await flushPromises()

    expect(urls()).toEqual([DIGEST_MANUAL])
  })
})
