/**
 * First-login wizard: the window, the moves between steps, the name and the save at
 * the end. Fictional member « Alice », answers of the server faked.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import {
  api,
  auth,
  backButton,
  heading,
  member,
  next,
  nextButton,
  openWizard,
  plain,
  resetBench,
  serverAnswers,
  showToast,
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

const NEW = { display_name: 'Renard-Bleu-42', display_name_must_set: true }
const wrappers = []
const open = async (...args) => {
  const wrapper = await openWizard(...args)
  wrappers.push(wrapper)
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

describe('PortalOnboardingWizard, the window', () => {
  it('is a named dialog that starts on the welcome, its title focused', async () => {
    serverAnswers()
    const wrapper = await open(member(NEW))

    const dialog = wrapper.get('[role="dialog"]')
    expect(dialog.attributes('aria-modal')).toBe('true')
    expect(wrapper.get(`#${dialog.attributes('aria-labelledby')}`).text()).toBe(
      'Assistant de première connexion',
    )
    expect(heading(wrapper)).toBe('Bienvenue sur MediaKeeper')
    expect(wrapper.text()).toContain('Première connexion')
    await vi.advanceTimersByTimeAsync(0)
    expect(document.activeElement).toBe(wrapper.get('h1').element)
    expect(backButton(wrapper).exists()).toBe(false)
    expect(nextButton(wrapper).text()).toBe('Commencer')
  })

  it('cannot be closed: no cross, Escape does nothing', async () => {
    serverAnswers()
    const wrapper = await open(member(NEW))

    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))
    await flushPromises()

    expect(wrapper.find('[aria-label="Fermer"]').exists()).toBe(false)
    expect(wrapper.emitted('done')).toBeUndefined()
  })

  it('counts the nine steps between welcome and done, and moves the focus to each title', async () => {
    serverAnswers()
    const wrapper = await open(member())
    await next(wrapper)
    await vi.advanceTimersByTimeAsync(0)

    const bar = wrapper.get('[role="progressbar"]')
    expect(bar.attributes()).toMatchObject({ 'aria-valuenow': '1', 'aria-valuemax': '9' })
    expect(wrapper.get('.wz-count').text()).toBe('Étape 1 sur 9')
    expect(plain(document.activeElement.textContent.trim())).toBe(
      'Comment devons-nous vous appeler ?',
    )
  })
})

describe('PortalOnboardingWizard, the name', () => {
  it('starts empty for a new account, the button off until the server agrees', async () => {
    serverAnswers({ verdicts: { Bruno: { reason: 'free', available: true } } })
    const wrapper = await open(member(NEW))
    await next(wrapper)

    const input = wrapper.get('.wz-input')
    expect(input.element.value).toBe('')
    expect(input.attributes('aria-invalid')).toBe('false')
    expect(nextButton(wrapper).attributes('disabled')).toBeDefined()

    await input.setValue('Bruno')
    expect(wrapper.get('.wz-msg').text()).toBe('Vérification…')
    expect(nextButton(wrapper).attributes('disabled')).toBeDefined()

    await vi.advanceTimersByTimeAsync(400)
    await flushPromises()
    expect(wrapper.get('.wz-msg').text()).toBe('Disponible')
    expect(nextButton(wrapper).attributes('disabled')).toBeUndefined()
    expect(nextButton(wrapper).text()).toBe('Confirmer')
  })

  it('says why a name is refused, once, and offers at most three free names', async () => {
    serverAnswers({
      verdicts: {
        Al: { reason: 'too_short' },
        Bob: { reason: 'taken', suggestions: ['Bob2', 'Bob3', 'Bob4', 'Bob5', 'Bob6'] },
      },
    })
    const wrapper = await open(member(NEW))
    await next(wrapper)

    await typeName(wrapper, 'Al')
    expect(wrapper.get('.wz-msg').text()).toBe('3 caractères minimum')
    expect(wrapper.get('.wz-input').attributes('aria-invalid')).toBe('true')

    await typeName(wrapper, 'Bob')
    expect(wrapper.get('.wz-msg').text()).toBe('Déjà utilisé par un autre membre.')
    const chips = wrapper.findAll('.wz-sugg .wz-chip')
    expect(chips.map(chip => chip.text())).toEqual(['Bob2', 'Bob3', 'Bob4'])

    await chips[0].trigger('click')
    expect(wrapper.get('.wz-input').element.value).toBe('Bob2')
  })

  it('says when the check got no answer, and tries again on demand', async () => {
    api.apiGet.mockRejectedValueOnce(new Error('http_503'))
    const wrapper = await open(member(NEW))
    await next(wrapper)
    await typeName(wrapper, 'Bruno')

    expect(wrapper.get('.wz-msg').text()).toContain('La vérification n’a pas abouti.')
    expect(nextButton(wrapper).attributes('disabled')).toBeDefined()

    serverAnswers({ verdicts: { Bruno: { reason: 'free', available: true } } })
    await wrapper.get('.wz-msg .wz-link').trigger('click')
    await vi.advanceTimersByTimeAsync(400)
    await flushPromises()
    expect(wrapper.get('.wz-msg').text()).toBe('Disponible')
  })

  it('keeps the current name of an existing account with one click', async () => {
    serverAnswers({ verdicts: { Alice: { reason: 'current', available: true } } })
    const wrapper = await open(member())
    await vi.advanceTimersByTimeAsync(400)
    await next(wrapper)

    expect(wrapper.get('.wz-input').element.value).toBe('Alice')
    expect(plain(wrapper.get('.wz-msg').text())).toBe(
      'C’est votre pseudo actuel : vous pouvez le garder.',
    )
    expect(nextButton(wrapper).text()).toBe('Garder ce pseudo')
  })

  it('shows a name changed less than six months ago read-only, with its date', async () => {
    serverAnswers({ lock: '2027-03-31T10:00:00Z' })
    const wrapper = await open(member({ display_name_changed_at: '2026-10-02T10:00:00Z' }))
    await next(wrapper)

    expect(wrapper.get('.wz-input').attributes('readonly')).toBeDefined()
    expect(plain(wrapper.get('.wz-msg').text())).toBe(
      'Vous avez changé de pseudo il y a moins de 6 mois : vous pourrez le modifier à partir du 31 mars 2027.',
    )
    expect(wrapper.find('.wz-note--warn').exists()).toBe(false)
    expect(nextButton(wrapper).text()).toBe('Suivant')
  })
})

describe('PortalOnboardingWizard, the end', () => {
  async function toDone(profile, verdicts) {
    serverAnswers({ verdicts })
    const wrapper = await open(profile)
    await next(wrapper)
    await typeName(wrapper, 'Bruno')
    return walkTo(wrapper, 'C’est parti, Bruno !')
  }

  it('sends every choice at once, then hands over', async () => {
    const saved = member({ display_name: 'Bruno', onboarding_pending: false })
    api.apiPost.mockResolvedValue(saved)
    const wrapper = await toDone(member(NEW), { Bruno: { reason: 'free', available: true } })

    expect(plain(wrapper.text())).toContain(
      'Vérifiez vos choix : ils sont enregistrés quand vous continuez.',
    )
    expect(api.apiPost).not.toHaveBeenCalled()
    await next(wrapper)

    expect(api.apiPost).toHaveBeenCalledWith('/api/portal/profiles/me/onboarding', {
      display_name: 'Bruno',
      language: null,
      is_public: true,
      favorite_genres: [],
    })
    expect(auth.replaceProfile).toHaveBeenCalledWith(saved)
    expect(wrapper.emitted('done')).toHaveLength(1)
  })

  it('hands over before the new profile closes it', async () => {
    api.apiPost.mockResolvedValue(member({ display_name: 'Bruno', onboarding_pending: false }))
    const wrapper = await toDone(member(NEW), { Bruno: { reason: 'free', available: true } })
    // As on the page: the saved profile clears the flag, and the wizard is gone.
    let doneWhenReplaced = null
    auth.replaceProfile.mockImplementation(() => {
      doneWhenReplaced = wrapper.emitted('done')?.length ?? 0
      wrapper.unmount()
    })

    await next(wrapper)

    expect(doneWhenReplaced).toBe(1)
  })

  it('goes back to the name a member took meanwhile, with free names', async () => {
    api.apiPost.mockRejectedValue(new Error('display_name_taken'))
    const wrapper = await toDone(member(NEW), { Bruno: { reason: 'free', available: true } })
    serverAnswers({ verdicts: { Bruno: { reason: 'taken', suggestions: ['Bruno2'] } } })

    await next(wrapper)
    await vi.advanceTimersByTimeAsync(400)
    await flushPromises()

    expect(heading(wrapper)).toBe('Comment devons-nous vous appeler ?')
    expect(wrapper.get('.wz-msg').text()).toBe('Déjà utilisé par un autre membre.')
    expect(wrapper.findAll('.wz-sugg .wz-chip').map(chip => chip.text())).toEqual(['Bruno2'])
    expect(wrapper.emitted('done')).toBeUndefined()
  })

  it('stays open on another failure, and lets the person try again', async () => {
    api.apiPost.mockRejectedValueOnce(new Error('http_500'))
    const wrapper = await toDone(member(NEW), { Bruno: { reason: 'free', available: true } })

    await next(wrapper)
    expect(wrapper.get('.wz-error').text()).toContain('L’enregistrement n’a pas abouti.')
    expect(wrapper.emitted('done')).toBeUndefined()

    api.apiPost.mockResolvedValue(member({ display_name: 'Bruno' }))
    await next(wrapper)
    expect(wrapper.emitted('done')).toHaveLength(1)
  })

  it('takes the edit of a choice back to its step', async () => {
    const wrapper = await toDone(member(NEW), { Bruno: { reason: 'free', available: true } })

    await wrapper.get('[aria-label="Modifier la langue"]').trigger('click')

    expect(heading(wrapper)).toBe('Dans quelle langue préférez-vous le portail ?')
  })
})

describe('PortalOnboardingWizard, a name reset by an administrator', () => {
  it('asks the name alone and saves it as the settings do', async () => {
    serverAnswers({ verdicts: { Bruno: { reason: 'free', available: true } } })
    const saved = member({ display_name: 'Bruno' })
    api.apiPut.mockResolvedValue(saved)
    const wrapper = await open(member({ ...NEW, display_name: 'Alice_42' }), 'reset')

    expect(heading(wrapper)).toBe('Choisissez un nouveau pseudo')
    expect(plain(wrapper.text())).toContain('« Alice_42 »')
    expect(wrapper.find('[role="progressbar"]').exists()).toBe(false)
    expect(wrapper.find('.wz-banner--sm').exists()).toBe(true)
    expect(wrapper.get('.wz-foot-hint').text()).toBe('Étape obligatoire')
    expect(backButton(wrapper).exists()).toBe(false)

    await typeName(wrapper, 'Bruno')
    expect(nextButton(wrapper).text()).toBe('Confirmer et continuer')
    await next(wrapper)

    expect(api.apiPut).toHaveBeenCalledWith('/api/portal/profiles/me', { display_name: 'Bruno' })
    expect(auth.replaceProfile).toHaveBeenCalledWith(saved)
    expect(wrapper.emitted('done')).toHaveLength(1)
    expect(showToast).not.toHaveBeenCalled()
  })
})
