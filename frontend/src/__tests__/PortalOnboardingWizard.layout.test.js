/**
 * First-login wizard: the step scrolls inside the window while its footer stays put, and
 * each new step opens at its top. Fictional member « Alice ».
 * Mounted with the real Teleport: the window keeps the same elements across steps, as in
 * the browser.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { WIZARD_MODE } from '@/constants/portalOnboarding'
import { member, openWizard, resetBench, serverAnswers } from './_onboardingWizardHarness'

vi.mock('@/composables/useApi', async () => {
  const { api } = await import('./_onboardingWizardSpies')
  return { useApi: () => api }
})
vi.mock('@/composables/portal/usePortalAuth', async () => {
  const { auth } = await import('./_onboardingWizardSpies')
  return { usePortalAuth: () => auth }
})
vi.mock('@/composables/portal/usePortalLocale', async () => {
  const { applyPortalLocale } = await import('./_onboardingWizardSpies')
  return { usePortalLocale: () => ({ applyPortalLocale }) }
})
vi.mock('@/composables/useToast', async () => {
  const { showToast } = await import('./_onboardingWizardSpies')
  return { useToast: () => ({ showToast }) }
})

const find = selector => document.body.querySelector(selector)

let wrapper
beforeEach(async () => {
  resetBench()
  vi.useFakeTimers()
  serverAnswers({ verdicts: { Alice: { reason: 'current', available: true } } })
  wrapper = await openWizard(member(), WIZARD_MODE.FULL, { realTeleport: true })
})
afterEach(() => {
  wrapper.unmount()
  vi.useRealTimers()
})

describe('PortalOnboardingWizard, the window', () => {
  it('keeps the footer out of the part that scrolls', () => {
    expect(find('.wz-in .wz-step')).not.toBeNull()
    expect(find('.wz-in .wz-foot')).toBeNull()
    expect(find('.wz').lastElementChild).toBe(find('.wz-foot'))
  })

  it('opens the next step at its top, even when the last one was scrolled down', async () => {
    const body = find('.wz-in')
    // jsdom does no layout: its scrollTop stays 0, so the test gives it a position.
    Object.defineProperty(body, 'scrollTop', { value: 640, writable: true })

    find('.wz-next').click()
    await flushPromises()

    expect(find('.wz-step').classList).toContain('wz-step--name')
    expect(find('.wz-in')).toBe(body)
    expect(body.scrollTop).toBe(0)
  })
})
