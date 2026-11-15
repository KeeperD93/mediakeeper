/**
 * First-login wizard, the focus trap: Tab and Shift+Tab stay inside the window (it cannot
 * be closed: Escape is covered by the flow tests). Fictional member « Alice ».
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  member,
  next,
  nextButton,
  openWizard,
  resetBench,
  serverAnswers,
} from './_onboardingWizardHarness'

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

const wrappers = []
const tab = (shiftKey = false) =>
  document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Tab', shiftKey, bubbles: true }))

/** The name step of an existing account: the field, then « Back » and the main button. */
async function nameStep() {
  serverAnswers({ verdicts: { Alice: { reason: 'current', available: true } } })
  const wrapper = await openWizard(member())
  wrappers.push(wrapper)
  await vi.advanceTimersByTimeAsync(400)
  await next(wrapper)
  return wrapper
}

beforeEach(() => {
  resetBench()
  vi.useFakeTimers()
})
afterEach(() => {
  wrappers.splice(0).forEach(wrapper => wrapper.unmount())
  vi.useRealTimers()
})

describe('PortalOnboardingWizard, the focus trap', () => {
  it('wraps Tab from the main button back to the field', async () => {
    const wrapper = await nameStep()

    nextButton(wrapper).element.focus()
    tab()

    expect(document.activeElement).toBe(wrapper.get('.wz-input').element)
  })

  it('wraps Shift+Tab from the field to the main button', async () => {
    const wrapper = await nameStep()

    wrapper.get('.wz-input').element.focus()
    tab(true)

    expect(document.activeElement).toBe(nextButton(wrapper).element)
  })

  it('wraps Shift+Tab from the step title, where the focus lands, to the main button', async () => {
    const wrapper = await nameStep()
    await vi.advanceTimersByTimeAsync(0)
    expect(document.activeElement).toBe(wrapper.get('h1').element)

    tab(true)

    expect(document.activeElement).toBe(nextButton(wrapper).element)
  })
})
