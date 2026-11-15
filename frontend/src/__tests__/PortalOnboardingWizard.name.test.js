/**
 * First-login wizard, the name by account: a name reset before the tour, a lock not known
 * yet, a locked name the save refuses, and the reset alone refused. Fictional member
 * « Alice », answers of the server faked.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import {
  api,
  auth,
  heading,
  member,
  next,
  nextButton,
  openWizard,
  resetBench,
  serverAnswers,
  typeName,
  walkTo,
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

const CHOSEN_AT = '2026-10-02T10:00:00Z'
const LOCK_END = '2027-03-31T10:00:00Z'
const LOCKED_TEXT =
  'Vous avez changé de pseudo il y a moins de 6 mois : vous pourrez le modifier à partir du 31 mars 2027.'
const RESET = { display_name: 'Alice_42', display_name_must_set: true }
const wrappers = []
const open = async (...args) => {
  const wrapper = await openWizard(...args)
  wrappers.push(wrapper)
  return wrapper
}
const input = wrapper => wrapper.get('.wz-input')
const message = wrapper => wrapper.get('.wz-msg').text()
const isOff = button => button.attributes('disabled') !== undefined

/** `username-state` answers only when the test says so; other checks find the name current. */
function holdLock() {
  let answer
  api.apiGet.mockImplementation(url =>
    url.endsWith('/username-state')
      ? new Promise(resolve => {
          answer = resolve
        })
      : Promise.resolve({
          available: true,
          reason: 'current',
          locked_until: null,
          suggestions: [],
        }),
  )
  return lockedUntil => answer({ locked: !!lockedUntil, locked_until: lockedUntil })
}

async function openOnName(profile) {
  const wrapper = await open(profile)
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

describe('PortalOnboardingWizard, a name reset before the tour', () => {
  it('greets the member as an existing one and asks a new name, the field empty', async () => {
    serverAnswers()
    const wrapper = await open(member({ ...RESET, display_name_changed_at: CHOSEN_AT }))

    expect(wrapper.text()).toContain('Visite guidée')
    expect(wrapper.text()).not.toContain('Première connexion')
    await next(wrapper)

    expect(input(wrapper).element.value).toBe('')
    expect(input(wrapper).attributes('placeholder')).toBe('Votre nouveau pseudo')
    expect(wrapper.get('.dd-sub').text()).toContain(
      'Un administrateur a réinitialisé votre pseudo « Alice_42 »',
    )
    expect(wrapper.get('.wz-note').text()).toBe(
      'En attendant, les autres membres voient un pseudo provisoire tiré au hasard.',
    )
  })

  it('still welcomes a name never chosen as a first login', async () => {
    serverAnswers()
    const wrapper = await open(member(RESET))

    expect(wrapper.text()).toContain('Première connexion')
    await next(wrapper)
    expect(input(wrapper).attributes('placeholder')).toBe('Votre pseudo')
  })
})

describe('PortalOnboardingWizard, a lock not known yet', () => {
  it('offers nothing on the name until the server says, then shows the lock', async () => {
    const answerLock = holdLock()
    const wrapper = await openOnName(member({ display_name_changed_at: CHOSEN_AT }))

    expect(input(wrapper).attributes('readonly')).toBeDefined()
    expect(message(wrapper)).toBe('Vérification…')
    expect(isOff(nextButton(wrapper))).toBe(true)

    answerLock(LOCK_END)
    await flushPromises()
    expect(message(wrapper)).toBe(LOCKED_TEXT)
    expect(isOff(nextButton(wrapper))).toBe(false)
    expect(nextButton(wrapper).text()).toBe('Suivant')
  })

  it('opens the field once the server says the name is free to change', async () => {
    const answerLock = holdLock()
    const wrapper = await openOnName(member())

    answerLock(null)
    await flushPromises()
    expect(input(wrapper).attributes('readonly')).toBeUndefined()
    expect(message(wrapper)).toBe('C’est votre pseudo actuel : vous pouvez le garder.')
    expect(nextButton(wrapper).text()).toBe('Garder ce pseudo')
    expect(isOff(nextButton(wrapper))).toBe(false)
  })

  it('opens the field when the lock cannot be read, the live check answering instead', async () => {
    serverAnswers({ verdicts: { Alice: { reason: 'current', available: true } } })
    const answers = api.apiGet.getMockImplementation()
    api.apiGet.mockImplementation(url =>
      url.endsWith('/username-state') ? Promise.reject(new Error('http_503')) : answers(url),
    )
    const wrapper = await openOnName(member())

    expect(input(wrapper).attributes('readonly')).toBeUndefined()
    expect(nextButton(wrapper).text()).toBe('Garder ce pseudo')
    expect(isOff(nextButton(wrapper))).toBe(false)
  })
})

describe('PortalOnboardingWizard, a locked name at the end', () => {
  it('sends the stored name unchanged', async () => {
    serverAnswers({ lock: LOCK_END })
    api.apiPost.mockResolvedValue(member({ onboarding_pending: false }))
    const wrapper = await open(member({ display_name_changed_at: CHOSEN_AT }))

    await walkTo(wrapper, 'C’est parti, Alice !')
    await next(wrapper)

    expect(api.apiPost).toHaveBeenCalledWith(
      '/api/portal/profiles/me/onboarding',
      expect.objectContaining({ display_name: 'Alice' }),
    )
    expect(wrapper.emitted('done')).toHaveLength(1)
  })

  it('opens a locked name the save refuses, says why, and takes another', async () => {
    serverAnswers({ lock: LOCK_END })
    api.apiPost.mockRejectedValueOnce(new Error('display_name_reserved'))
    const wrapper = await open(
      member({ display_name: 'Admin Bob', display_name_changed_at: CHOSEN_AT }),
    )
    await walkTo(wrapper, 'C’est parti, Admin Bob !')
    await next(wrapper)

    expect(heading(wrapper)).toBe('Comment devons-nous vous appeler ?')
    expect(input(wrapper).attributes('readonly')).toBeUndefined()
    expect(message(wrapper)).toBe('Ce pseudo est réservé.')
    expect(isOff(nextButton(wrapper))).toBe(true)

    serverAnswers({ verdicts: { Bruno: { reason: 'free', available: true } } })
    api.apiPost.mockResolvedValue(member({ display_name: 'Bruno', onboarding_pending: false }))
    await typeName(wrapper, 'Bruno')
    await walkTo(wrapper, 'C’est parti, Bruno !')
    await next(wrapper)

    expect(api.apiPost).toHaveBeenLastCalledWith(
      '/api/portal/profiles/me/onboarding',
      expect.objectContaining({ display_name: 'Bruno' }),
    )
    expect(wrapper.emitted('done')).toHaveLength(1)
  })
})

describe('PortalOnboardingWizard, the reset alone refused', () => {
  async function confirmReset(error) {
    // The live check said yes; the save, judging last, may still refuse.
    serverAnswers({ verdicts: { Alice_42: { reason: 'free', available: true } } })
    api.apiPut.mockRejectedValueOnce(new Error(error))
    const wrapper = await open(member({ ...RESET, display_name_changed_at: CHOSEN_AT }), 'reset')
    await typeName(wrapper, 'Alice_42')
    await next(wrapper)
    return wrapper
  }

  it('stays open on a name the save refuses, with the reason', async () => {
    const wrapper = await confirmReset('display_name_previous')

    expect(message(wrapper)).toBe(
      'C’est votre ancien pseudo : il a été réinitialisé par un administrateur, choisissez-en un nouveau.',
    )
    expect(isOff(nextButton(wrapper))).toBe(true)
    expect(auth.replaceProfile).not.toHaveBeenCalled()
    expect(wrapper.emitted('done')).toBeUndefined()
  })

  it('stays open when the save gets no answer, and saves on the next try', async () => {
    const wrapper = await confirmReset('http_500')

    expect(wrapper.get('.wz-error').text()).toContain('L’enregistrement n’a pas abouti.')
    expect(wrapper.emitted('done')).toBeUndefined()

    api.apiPut.mockResolvedValue(member({ display_name: 'Alice_42', display_name_must_set: false }))
    await next(wrapper)
    expect(wrapper.emitted('done')).toHaveLength(1)
  })
})
