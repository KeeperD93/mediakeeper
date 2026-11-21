/**
 * Shared bench of the first-login wizard tests: fictional profiles, the server's
 * answers, and a mount with the real translations (French) so the texts read as shown.
 * The test files mock useApi, usePortalAuth, usePortalLocale and useToast with the
 * spies below (vi.mock stays in each file: it is hoisted there).
 */
import { vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import i18n from '@/i18n'
import PortalOnboardingWizard from '@/components/portal/wizard/PortalOnboardingWizard.vue'
import { WIZARD_MODE } from '@/constants/portalOnboarding'
import { api, auth, applyPortalLocale, showToast } from './_onboardingWizardSpies'

export { api, auth, applyPortalLocale, showToast }

export function member(overrides = {}) {
  return {
    id: 7,
    user_id: 7,
    role: 'user',
    display_name: 'Alice',
    display_name_must_set: false,
    display_name_changed_at: null,
    onboarding_pending: true,
    language: null,
    effective_language: 'fr',
    is_public: true,
    forced_public: false,
    favorite_genres: [],
    avatar_url: null,
    avatar_is_custom: false,
    tier: 'bronze',
    level: 12,
    xp: 1140,
    created_at: '2026-03-02T10:00:00Z',
    access_end_date: null,
    ...overrides,
  }
}

/** The server's live verdicts, by name; `username-state` says whether the name is locked. */
export function serverAnswers({ verdicts = {}, lock = null } = {}) {
  api.apiGet.mockImplementation(async url => {
    if (url.endsWith('/username-state')) {
      return lock
        ? { locked: true, locked_until: lock, must_set: false, lock_days: 180 }
        : { locked: false, locked_until: null, must_set: false, lock_days: 180 }
    }
    const name = decodeURIComponent(url.split('name=')[1])
    return {
      available: false,
      reason: 'free',
      locked_until: null,
      suggestions: [],
      ...verdicts[name],
    }
  })
}

export function resetBench() {
  vi.clearAllMocks()
  auth.profile.value = null
  api.apiGet.mockReset()
  api.apiPost.mockReset()
  api.apiPut.mockReset()
  api.apiFetch.mockReset()
  auth.replaceProfile.mockReset()
  i18n.global.locale.value = 'fr'
}

/**
 * `realTeleport`: the window goes into document.body and keeps its elements from one
 * render to the next, as in the browser (setup.js's stub rebuilds them); read it from
 * the document then, the wrapper does not reach it.
 */
export async function openWizard(profile, mode = WIZARD_MODE.FULL, { realTeleport = false } = {}) {
  auth.profile.value = profile
  const wrapper = mount(PortalOnboardingWizard, {
    props: { mode },
    attachTo: document.body,
    global: {
      plugins: [i18n],
      mocks: { $t: i18n.global.t },
      stubs: realTeleport ? { Teleport: false } : {},
    },
  })
  await flushPromises()
  return wrapper
}

// French keeps « ? ! : ; » and guillemets with their words by a no-break space; the
// tests write a plain one.
const NBSP = String.fromCharCode(0xa0)
export const plain = text => text.replaceAll(NBSP, ' ')

export const heading = wrapper => plain(wrapper.get('h1').text())
export const nextButton = wrapper => wrapper.get('.wz-next')
export const backButton = wrapper => wrapper.find('.wz-foot .wz-ghost')

export async function next(wrapper) {
  await nextButton(wrapper).trigger('click')
  await flushPromises()
}

/** Type a name and let the pause before the check pass (fake timers). */
export async function typeName(wrapper, value) {
  await wrapper.get('.wz-input').setValue(value)
  await vi.advanceTimersByTimeAsync(400)
  await flushPromises()
}

/** Walk the tour from the welcome screen to `title` (French title of a step). */
export async function walkTo(wrapper, title, guard = 20) {
  for (let i = 0; i < guard && heading(wrapper) !== title; i += 1) await next(wrapper)
  return wrapper
}
