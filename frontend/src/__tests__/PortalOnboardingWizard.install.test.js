/**
 * First-login wizard, last step: the box that offers to install the portal as an app,
 * under the recap. A button where the browser has its own window, the steps or another
 * browser to use elsewhere, nothing where it cannot be offered. Fictional member « Alice »;
 * the browser side is mocked.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  member,
  openWizard,
  plain,
  resetBench,
  serverAnswers,
  walkTo,
} from './_onboardingWizardHarness'
import { INSTALL_WAY } from '@/constants/portalInstall'

const browser = vi.hoisted(() => ({ way: null, steps: [], install: vi.fn() }))

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
vi.mock('@/composables/portal/useAppInstall', async () => {
  const { ref } = await import('vue')
  return {
    useAppInstall: () => ({
      way: ref(browser.way),
      steps: ref(browser.steps),
      install: browser.install,
    }),
  }
})

const DONE = 'C’est parti, Alice !'

const wrappers = []
async function lastStep() {
  serverAnswers({ verdicts: { Alice: { reason: 'current', available: true } } })
  const wrapper = await openWizard(member())
  wrappers.push(wrapper)
  await vi.advanceTimersByTimeAsync(400)
  return walkTo(wrapper, DONE)
}
const boxes = wrapper => wrapper.findAll('.wz-next-box').map(box => plain(box.text()))

beforeEach(() => {
  resetBench()
  vi.useFakeTimers()
  Object.assign(browser, { way: null, steps: [] })
})
afterEach(() => {
  wrappers.splice(0).forEach(wrapper => wrapper.unmount())
  vi.useRealTimers()
})

describe('PortalOnboardingWizard, installing the app', () => {
  it('opens the browser’s window from a button, under the recap', async () => {
    browser.way = INSTALL_WAY.PROMPT
    const wrapper = await lastStep()

    expect(boxes(wrapper)).toHaveLength(2)
    expect(boxes(wrapper)[0]).toContain('Installer l’application')
    expect(boxes(wrapper)[0]).toContain('Ouvrez MediaKeeper depuis son icône')
    // Between the recap and what opens next.
    expect(wrapper.get('.wz-recap + .wz-next-box').text()).toContain('Installer')
    await wrapper.get('.wz-install').trigger('click')
    expect(browser.install).toHaveBeenCalledTimes(1)
  })

  it('shows the steps on an iPhone, without a button', async () => {
    browser.way = INSTALL_WAY.IOS
    browser.steps = ['portal.appInstall.ios', 'portal.appInstall.iosNotify']
    const wrapper = await lastStep()

    const box = boxes(wrapper)[0]
    expect(box).toContain('Touchez le bouton Partager, puis « Sur l’écran d’accueil ».')
    expect(box).toContain('c’est aussi ce qui permet de recevoir les notifications')
    expect(wrapper.find('.wz-install').exists()).toBe(false)
  })

  it.each([
    ['the Dock steps in Safari on a Mac', INSTALL_WAY.MAC, 'mac', '« Ajouter au Dock »'],
    [
      'the menu steps in Firefox on Android',
      INSTALL_WAY.FIREFOX_ANDROID,
      'firefoxAndroid',
      'Dans le menu de Firefox (les trois points)',
    ],
    [
      'another browser to Firefox on a computer',
      INSTALL_WAY.OTHER_BROWSER,
      'otherBrowser',
      'ouvrez le portail dans Chrome ou Edge pour l’installer',
    ],
  ])('shows %s, without a button', async (_, way, key, text) => {
    browser.way = way
    browser.steps = [`portal.appInstall.${key}`]
    const wrapper = await lastStep()

    expect(boxes(wrapper)[0]).toContain(text)
    expect(wrapper.find('.wz-install').exists()).toBe(false)
  })

  it('offers nothing where the browser cannot install, what opens next stays', async () => {
    const wrapper = await lastStep()

    expect(boxes(wrapper)).toHaveLength(1)
    expect(boxes(wrapper)[0]).toContain('Et maintenant')
  })
})
