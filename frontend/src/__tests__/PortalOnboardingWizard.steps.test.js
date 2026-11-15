/**
 * First-login wizard: what each step shows and keeps (language, visibility, account end,
 * notifications, genres, image) and how the recap reads it. Fictional member « Alice ».
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import {
  api,
  applyPortalLocale,
  auth,
  heading,
  member,
  next,
  openWizard,
  resetBench,
  serverAnswers,
  showToast,
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

const TITLE = {
  language: 'Dans quelle langue préférez-vous le portail ?',
  visibility: 'Qui peut voir votre profil ?',
  expiry: 'Jusqu’à quand votre compte est-il ouvert ?',
  notifications: 'Voulez-vous être prévenu ?',
  genres: 'Qu’aimez-vous regarder ?',
  avatar: 'Une image pour votre profil ?',
  done: 'C’est parti, Alice !',
}

const wrappers = []
async function stepOf(title, profile = member(), mode) {
  serverAnswers({ verdicts: { Alice: { reason: 'current', available: true } } })
  const wrapper = await openWizard(profile, mode)
  wrappers.push(wrapper)
  await vi.advanceTimersByTimeAsync(400)
  return walkTo(wrapper, title)
}
const radios = wrapper => wrapper.findAll('.wz-radio')
/** Put `file` in the image field, as the browser's picker does. */
async function pickFile(wrapper, file) {
  const input = wrapper.get('.wz-file')
  Object.defineProperty(input.element, 'files', { value: [file], configurable: true })
  await input.trigger('change')
}
const image = name => new File(['x'], name, { type: 'image/png' })
const recapValue = (wrapper, label) =>
  wrapper
    .findAll('.wz-rrow')
    .find(row => row.get('.wz-rl').text() === label)
    .get('.wz-rv')
    .text()

beforeEach(() => {
  resetBench()
  vi.useFakeTimers()
})
afterEach(() => {
  wrappers.splice(0).forEach(wrapper => wrapper.unmount())
  vi.useRealTimers()
  vi.unstubAllGlobals()
})

describe('PortalOnboardingWizard, the language', () => {
  it('names the instance language behind « Default », and each language in its own words', async () => {
    const wrapper = await stepOf(TITLE.language)

    const hints = wrapper.findAll('.wz-oh').map(hint => hint.text())
    expect(hints[0]).toBe('Suit la langue choisie par l’administrateur, aujourd’hui le français.')
    expect(hints[2]).toBe('The portal, recommendations and trailers switch to English.')
    expect(wrapper.findAll('.wz-oh')[2].attributes('lang')).toBe('en')
  })

  it('switches the portal as soon as the step is left, without saving', async () => {
    const wrapper = await stepOf(TITLE.language)

    await radios(wrapper)[2].setValue(true)
    await next(wrapper)

    expect(applyPortalLocale).toHaveBeenCalledWith('en')
    expect(api.apiPost).not.toHaveBeenCalled()
  })
})

describe('PortalOnboardingWizard, the visibility', () => {
  it('greys the choice of a profile an administrator made public', async () => {
    const wrapper = await stepOf(TITLE.visibility, member({ forced_public: true }))

    expect(radios(wrapper).every(radio => radio.element.disabled)).toBe(true)
    expect(wrapper.text()).toContain('Visibilité forcée par un administrateur.')
  })

  it('explains what a private profile keeps', async () => {
    const wrapper = await stepOf(TITLE.visibility)

    await radios(wrapper)[1].setValue(true)

    expect(wrapper.get('[role="status"]').text()).toContain('Vos points d’expérience continuent')
  })
})

describe('PortalOnboardingWizard, the account end', () => {
  it('reads the real account, and warns in amber once an end date exists', async () => {
    vi.setSystemTime(new Date('2026-11-13T12:00:00'))
    const wrapper = await stepOf(TITLE.expiry, member({ access_end_date: '2026-12-12T12:00:00' }))

    expect(wrapper.get('.wz-set').text()).toContain('2 mars 2026')
    // French groups thousands with a narrow space.
    expect(wrapper.get('.wz-set').text().replace(/\s/g, ' ')).toContain('12 · 1 140 XP')
    expect(wrapper.get('.dd-expiry').text()).toContain(
      'Votre compte expire le 12 décembre 2026, dans 29 jours.',
    )
  })

  it('says there is no end date', async () => {
    const wrapper = await stepOf(TITLE.expiry)

    expect(wrapper.get('.wz-set .is-hl').text()).toContain('Aucune limite')
    expect(wrapper.find('.dd-expiry').exists()).toBe(false)
  })
})

describe('PortalOnboardingWizard, the notifications', () => {
  function browser(permission, answer = permission) {
    const Notification = { permission, requestPermission: vi.fn() }
    Notification.requestPermission.mockImplementation(async () => {
      Notification.permission = answer
      return answer
    })
    vi.stubGlobal('Notification', Notification)
    vi.stubGlobal('isSecureContext', true)
    return Notification
  }

  it('asks the browser, then goes on without a word once allowed', async () => {
    const notification = browser('default', 'granted')
    const wrapper = await stepOf(TITLE.notifications)

    await wrapper.get('.wz-ask').trigger('click')
    await flushPromises()

    expect(notification.requestPermission).toHaveBeenCalledTimes(1)
    expect(wrapper.get('.wz-note--ok').text()).toBe('Notifications activées sur cet appareil.')
    await next(wrapper)
    expect(heading(wrapper)).toBe(TITLE.genres)
  })

  it('asks « are you sure? » before going on without them', async () => {
    browser('default')
    const wrapper = await stepOf(TITLE.notifications)

    await next(wrapper)
    expect(heading(wrapper)).toBe(TITLE.notifications)
    expect(wrapper.get('[role="alert"]').text()).toContain('Êtes-vous sûr ?')
    expect(wrapper.get('[role="alert"]').text()).toContain('Réessayer')

    await wrapper.findAll('[role="alert"] .wz-ghost').at(-1).trigger('click')
    expect(heading(wrapper)).toBe(TITLE.genres)
  })

  it('offers no retry once the browser refused for good', async () => {
    browser('default', 'denied')
    const wrapper = await stepOf(TITLE.notifications)

    await wrapper.get('.wz-ask').trigger('click')
    await flushPromises()

    expect(wrapper.get('[role="alert"]').text()).not.toContain('Réessayer')
    expect(wrapper.text()).toContain('Votre navigateur bloque les notifications de ce site.')
  })

  it('explains a browser without them, and goes on without asking', async () => {
    vi.stubGlobal('isSecureContext', true)
    const wrapper = await stepOf(TITLE.notifications)

    expect(wrapper.text()).toContain('Sur iPhone ou iPad, ajoutez d’abord le portail')
    await next(wrapper)
    expect(heading(wrapper)).toBe(TITLE.genres)
  })
})

describe('PortalOnboardingWizard, genres and image', () => {
  it('keeps the genres of Settings, with their TMDB ids', async () => {
    const wrapper = await stepOf(TITLE.genres, member({ favorite_genres: [35] }))

    const chips = wrapper.findAll('.wz-chip')
    expect(chips.find(chip => chip.text() === 'Comédie').attributes('aria-pressed')).toBe('true')
    await chips.find(chip => chip.text() === 'Action').trigger('click')

    expect(wrapper.get('.wz-where').text()).toContain('2 genres choisis')
    await walkTo(wrapper, TITLE.done)
    api.apiPost.mockResolvedValue(member())
    await next(wrapper)
    expect(api.apiPost.mock.calls[0][1].favorite_genres).toEqual([35, 28, 10759])
  })

  it('refuses a file that is no image or too heavy, at once', async () => {
    const wrapper = await stepOf(TITLE.avatar)
    await radios(wrapper)[1].setValue(true)

    await pickFile(wrapper, new File(['x'], 'notes.txt', { type: 'text/plain' }))
    expect(wrapper.get('.wz-upload [role="alert"]').text()).toContain('n’est pas une image')

    const heavy = image('big.png')
    Object.defineProperty(heavy, 'size', { value: 6 * 1024 * 1024 })
    await pickFile(wrapper, heavy)
    expect(wrapper.get('.wz-upload [role="alert"]').text()).toContain('dépasse 5 Mo')
  })

  it('sends the picked image after the choices; a failed upload still ends the wizard', async () => {
    vi.stubGlobal('URL', { createObjectURL: () => 'blob:preview', revokeObjectURL: vi.fn() })
    const wrapper = await stepOf(TITLE.avatar)
    await radios(wrapper)[1].setValue(true)
    await pickFile(wrapper, image('me.png'))
    expect(wrapper.get('.wz-av img').attributes('src')).toBe('blob:preview')

    await walkTo(wrapper, TITLE.done)
    expect(recapValue(wrapper, 'Avatar')).toBe('Votre image')
    api.apiPost.mockResolvedValue(member({ onboarding_pending: false }))
    api.apiFetch.mockRejectedValue(new Error('avatar_too_large'))
    await next(wrapper)

    expect(api.apiFetch.mock.calls[0][0]).toBe('/api/portal/profiles/me/avatar')
    expect(showToast).toHaveBeenCalledWith(
      'Votre image n’a pas pu être envoyée. Recommencez dans Paramètres › Identité.',
      'warn',
    )
    expect(auth.replaceProfile).toHaveBeenCalledWith(member({ onboarding_pending: false }))
    expect(wrapper.emitted('done')).toHaveLength(1)
  })

  it('puts the sent image on the saved profile', async () => {
    vi.stubGlobal('URL', { createObjectURL: () => 'blob:preview', revokeObjectURL: vi.fn() })
    const wrapper = await stepOf(TITLE.avatar)
    await radios(wrapper)[1].setValue(true)
    await pickFile(wrapper, image('me.png'))
    await walkTo(wrapper, TITLE.done)
    api.apiPost.mockResolvedValue(member({ onboarding_pending: false }))
    api.apiFetch.mockResolvedValue({ json: async () => ({ avatar_url: '/avatars/7.png' }) })

    await next(wrapper)

    expect(auth.replaceProfile).toHaveBeenCalledWith(
      member({ onboarding_pending: false, avatar_url: '/avatars/7.png', avatar_is_custom: true }),
    )
    expect(showToast).not.toHaveBeenCalled()
  })

  it('frees each preview once replaced, and the last one when the wizard goes', async () => {
    const revokeObjectURL = vi.fn()
    let made = 0
    vi.stubGlobal('URL', { createObjectURL: () => `blob:preview-${++made}`, revokeObjectURL })
    const wrapper = await stepOf(TITLE.avatar)
    await radios(wrapper)[1].setValue(true)

    await pickFile(wrapper, image('first.png'))
    await pickFile(wrapper, image('second.png'))
    expect(revokeObjectURL.mock.calls).toEqual([['blob:preview-1']])

    wrappers.splice(wrappers.indexOf(wrapper), 1)
    wrapper.unmount()
    expect(revokeObjectURL.mock.calls).toEqual([['blob:preview-1'], ['blob:preview-2']])
  })
})

describe('PortalOnboardingWizard, the recap', () => {
  it('reads each choice back', async () => {
    const wrapper = await stepOf(TITLE.done)

    expect(recapValue(wrapper, 'Pseudo')).toBe('Alice')
    expect(recapValue(wrapper, 'Langue')).toBe('Par défaut (français)')
    expect(recapValue(wrapper, 'Profil')).toBe('Public')
    expect(recapValue(wrapper, 'Genres préférés')).toBe('Aucun pour l’instant')
    expect(recapValue(wrapper, 'Avatar')).toBe('Image de votre compte Emby')
  })
})
