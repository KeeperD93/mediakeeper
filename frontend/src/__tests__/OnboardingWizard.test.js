/**
 * Setup wizard: language and time zone come first, a zone is saved on « Next », and each
 * tool step still saves what belongs to it.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

const apiGet = vi.fn()
const apiPut = vi.fn()
const apiFetch = vi.fn()
const confirm = vi.fn()
const showToast = vi.fn()
const setLocale = vi.fn()
vi.mock('@/composables/useApi', () => ({
  useApi: () => ({ apiGet, apiPut, apiFetch }),
  resolveApiError: (_message, fallback) => fallback,
}))
vi.mock('@/composables/useConfirm', () => ({ useConfirm: () => confirm }))
vi.mock('@/composables/useToast', () => ({ useToast: () => ({ showToast }) }))
vi.mock('vue-i18n', () => ({
  useI18n: () => ({
    t: (key, named) => {
      if (key.startsWith('settings.timezoneLine.')) return key.split('.').pop()
      return named?.zone ? `${key}:${named.zone}` : key
    },
  }),
}))
vi.mock('@/i18n', () => ({
  getLocale: () => 'fr',
  setLocale: (...args) => setLocale(...args),
  AVAILABLE_LOCALES: [
    { code: 'fr', label: 'Français', flag: 'FR' },
    { code: 'en', label: 'English', flag: 'EN' },
  ],
}))
vi.mock('@/utils/instanceTimezone', async importOriginal => ({
  ...(await importOriginal()),
  browserZone: () => 'Asia/Tokyo',
}))

import OnboardingWizard from '@/components/OnboardingWizard.vue'

const GROUPS = [
  { offset: 0, zones: ['UTC'] },
  { offset: 60, zones: ['Europe/Berlin', 'Europe/Paris'] },
  { offset: 540, zones: ['Asia/Seoul', 'Asia/Tokyo'] },
]
const NOT_SAVED = { timezone: null, effective: 'UTC', groups: GROUPS }
const SAVED = { timezone: 'Asia/Tokyo', effective: 'Asia/Tokyo', groups: GROUPS }
const ZONE_URL = '/api/system/timezone'
const TIME_ZONE_STEP = 'onboarding.stepLocale'

function serve({ zone = NOT_SAVED, onboardingDone = false, tools = {} } = {}) {
  const routes = {
    '/api/settings/tools': tools,
    '/api/settings/media-folders': [],
    '/api/onboarding/status': { authenticated: true, onboarding_done: onboardingDone },
    [ZONE_URL]: zone,
  }
  apiGet.mockImplementation(async url => {
    if (routes[url] === null) throw new Error('Test error')
    return routes[url]
  })
}

async function open(options) {
  serve(options)
  const wrapper = mount(OnboardingWizard)
  await flushPromises()
  return wrapper
}

const clickAndWait = async (wrapper, selector) => {
  await wrapper.get(selector).trigger('click')
  await flushPromises()
}
const next = wrapper => clickAndWait(wrapper, '.ob-btn-primary')
const skip = wrapper => clickAndWait(wrapper, '.ob-btn-skip')
const activeStep = wrapper => wrapper.get('.ob-nav-active .ob-nav-label').text()
const menus = wrapper => wrapper.findAll('select.ob-select')

async function openOnZoneStep(options) {
  const wrapper = await open(options)
  await next(wrapper)
  return wrapper
}

describe('OnboardingWizard', () => {
  beforeEach(() => {
    apiGet.mockReset()
    apiFetch.mockReset().mockResolvedValue({})
    apiPut.mockReset().mockImplementation(async (_url, { timezone }) => ({
      timezone,
      effective: timezone,
      groups: GROUPS,
    }))
    confirm.mockReset().mockResolvedValue(true)
    showToast.mockClear()
    setLocale.mockReset().mockResolvedValue(true)
  })

  it('asks for the language and the time zone before anything else to configure', async () => {
    const w = await open()
    expect(w.findAll('.ob-nav-label').map(label => label.text())).toEqual([
      'onboarding.stepWelcome',
      TIME_ZONE_STEP,
      'Emby',
      'TMDB',
      'OpenSubtitles',
      'onboarding.stepFolders',
      'onboarding.stepTour',
      'onboarding.stepDone',
    ])
    await next(w)
    expect(activeStep(w)).toBe(TIME_ZONE_STEP)
    expect(menus(w)).toHaveLength(2)
  })

  it('uses the shared menu arrow on both menus', async () => {
    const w = await openOnZoneStep()
    menus(w).forEach(menu => expect(menu.classes()).toContain('mk-select-chevron'))
  })

  it('names both menus for screen readers', async () => {
    const w = await openOnZoneStep()
    menus(w).forEach(menu => {
      const label = w.find(`label[for="${menu.attributes('id')}"]`)
      expect(label.exists()).toBe(true)
    })
  })

  it('changes the language at once, staying on the step', async () => {
    const w = await openOnZoneStep()
    await menus(w)[0].setValue('en')
    await flushPromises()
    expect(setLocale).toHaveBeenCalledWith('en')
    expect(activeStep(w)).toBe(TIME_ZONE_STEP)
  })

  it('offers the zone of the browser and saves a first choice without asking', async () => {
    const w = await openOnZoneStep()
    expect(menus(w)[1].element.selectedOptions[0].text).toBe('(UTC+09:00) Tokyo')
    await next(w)
    expect(confirm).not.toHaveBeenCalled()
    expect(apiPut).toHaveBeenCalledExactlyOnceWith(ZONE_URL, { timezone: 'Asia/Tokyo' })
    expect(activeStep(w)).toBe('Emby')
  })

  it('saves another row picked in the list', async () => {
    const w = await openOnZoneStep()
    await menus(w)[1].setValue('Amsterdam')
    await next(w)
    expect(apiPut).toHaveBeenCalledExactlyOnceWith(ZONE_URL, { timezone: 'Europe/Berlin' })
  })

  it('moves on without saving when the saved zone is kept', async () => {
    const w = await openOnZoneStep({ zone: SAVED })
    await next(w)
    expect(confirm).not.toHaveBeenCalled()
    expect(apiPut).not.toHaveBeenCalled()
    expect(activeStep(w)).toBe('Emby')
  })

  it('asks before changing a saved zone, then saves it', async () => {
    const w = await openOnZoneStep({ zone: SAVED })
    await menus(w)[1].setValue('Amsterdam')
    await next(w)
    expect(confirm).toHaveBeenCalledWith(
      expect.objectContaining({
        message: 'settings.timezoneConfirmMessage:(UTC+01:00) Amsterdam',
        variant: 'warn',
      }),
    )
    expect(apiPut).toHaveBeenCalledExactlyOnceWith(ZONE_URL, { timezone: 'Europe/Berlin' })
    expect(activeStep(w)).toBe('Emby')
  })

  it('stays on the step when the change of a saved zone is refused', async () => {
    confirm.mockResolvedValue(false)
    const w = await openOnZoneStep({ zone: SAVED })
    await menus(w)[1].setValue('Amsterdam')
    await next(w)
    expect(apiPut).not.toHaveBeenCalled()
    expect(activeStep(w)).toBe(TIME_ZONE_STEP)
  })

  it('stays on the step and says so when the server refuses the zone', async () => {
    apiPut.mockRejectedValue(new Error('invalid_timezone'))
    const w = await openOnZoneStep()
    await next(w)
    expect(activeStep(w)).toBe(TIME_ZONE_STEP)
    expect(showToast).toHaveBeenCalledTimes(1)
  })

  it('leaves the zone unsaved on « Skip », and the summary says so', async () => {
    const w = await openOnZoneStep()
    for (let step = 0; step < 6; step += 1) await skip(w)
    expect(apiPut).not.toHaveBeenCalled()
    const zoneRow = w.findAll('.ob-done-item')[0]
    expect(zoneRow.text()).toContain('settings.timezoneTitle')
    expect(zoneRow.classes()).toContain('skip')
    expect(zoneRow.text()).toContain('onboarding.skipped')
  })

  it('shows the zone as configured in the summary once saved', async () => {
    const w = await openOnZoneStep()
    await next(w)
    for (let step = 0; step < 5; step += 1) await skip(w)
    const zoneRow = w.findAll('.ob-done-item')[0]
    expect(zoneRow.classes()).toContain('ok')
    expect(zoneRow.text()).toContain('onboarding.configured')
  })

  it('shows a zone chosen earlier as configured when the wizard is run again', async () => {
    const w = await openOnZoneStep({ zone: SAVED })
    for (let step = 0; step < 6; step += 1) await skip(w)
    expect(w.findAll('.ob-done-item')[0].classes()).toContain('ok')
  })

  it('keeps the language and moves on when the zones cannot be read', async () => {
    const w = await openOnZoneStep({ zone: null })
    expect(menus(w)).toHaveLength(1)
    expect(showToast).toHaveBeenCalledTimes(1)
    await next(w)
    expect(apiPut).not.toHaveBeenCalled()
    expect(activeStep(w)).toBe('Emby')
  })

  it('does not read the zones while the wizard stays hidden', async () => {
    await open({ onboardingDone: true })
    expect(apiGet).not.toHaveBeenCalledWith(ZONE_URL)
  })

  it('saves each tool on its own step', async () => {
    const w = await openOnZoneStep({
      tools: {
        emby: { url: 'http://emby.test', api_key_configured: true },
        tmdb: { api_key_configured: true },
        opensubtitles: { api_key_configured: true },
      },
    })
    for (let step = 0; step < 4; step += 1) await next(w)
    expect(apiFetch.mock.calls.map(([url]) => url)).toEqual([
      '/api/settings/tools/emby',
      '/api/settings/tools/tmdb',
      '/api/settings/tools/opensubtitles',
    ])
    expect(activeStep(w)).toBe('onboarding.stepFolders')
  })

  it('offers « Finish » on the tour, then launches from the last step', async () => {
    const w = await openOnZoneStep()
    for (let step = 0; step < 5; step += 1) await skip(w)
    expect(activeStep(w)).toBe('onboarding.stepTour')
    expect(w.get('.ob-btn-primary').text()).toBe('onboarding.finish')
    await next(w)
    expect(w.find('.ob-btn-skip').exists()).toBe(false)
    expect(w.find('.ob-btn-primary').exists()).toBe(false)
    await clickAndWait(w, '.ob-btn-launch')
    expect(apiFetch).toHaveBeenCalledWith('/api/onboarding/complete', { method: 'POST' })
  })

  it('hides « Back » and « Skip » on the welcome step', async () => {
    const w = await open()
    expect(w.find('.ob-btn-ghost').exists()).toBe(false)
    expect(w.find('.ob-btn-skip').exists()).toBe(false)
  })
})
