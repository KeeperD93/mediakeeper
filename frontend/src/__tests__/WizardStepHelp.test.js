/**
 * First-login wizard, « Aides » step: the demo player (choice, loop, pause, still
 * mode for « reduce motion ») and the reduced screens, read with the real texts.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createI18n } from 'vue-i18n'
import en from '@/locales/en.json'
import fr from '@/locales/fr.json'

vi.mock('@/composables/useApi', () => ({ useApi: () => ({ apiGet: vi.fn() }) }))

import WizardStepHelp from '@/components/portal/wizard/WizardStepHelp.vue'

let wrapper

function mountStep(locale = 'fr') {
  const i18n = createI18n({ legacy: false, locale, messages: { fr, en } })
  wrapper = mount(WizardStepHelp, {
    props: { initial: 'A' },
    global: { plugins: [i18n], mocks: { $t: i18n.global.t } },
  })
  return wrapper
}

const chips = () => wrapper.findAll('.wzh-chip')
const captions = () => wrapper.findAll('.wzh-cap')
const litCaption = () => captions().findIndex(cap => cap.classes().includes('is-on'))
const shownViews = () => wrapper.findAll('.wzh-frame.is-shown')

function reduceMotion(matches) {
  vi.stubGlobal(
    'matchMedia',
    vi.fn(() => ({ matches, addEventListener: vi.fn(), removeEventListener: vi.fn() })),
  )
}

afterEach(() => {
  wrapper?.unmount()
  vi.useRealTimers()
  vi.unstubAllGlobals()
})

describe('WizardStepHelp — demos', () => {
  beforeEach(() => vi.useFakeTimers())

  it('offers three demos, the request one first, with its six captions', () => {
    mountStep()
    expect(chips().map(chip => chip.text())).toEqual([
      'Faire une demande',
      'Signaler un problème',
      'Créer une liste',
    ])
    expect(chips().map(chip => chip.attributes('aria-pressed'))).toEqual(['true', 'false', 'false'])
    expect(wrapper.find('.wzh-chips').attributes('aria-label')).toBe('Choisir une démonstration')
    expect(wrapper.find('.wzh-caps').attributes('aria-label')).toBe(
      'Faire une demande, étape par étape',
    )
    expect(captions()).toHaveLength(6)
    // No-break spaces keep « » and « : » with their words.
    expect(captions()[0].text()).toBe(
      '1Page d’accueil : un titre mis en avant se demande directement avec « Demander ».',
    )
    expect(litCaption()).toBe(0)
    expect(captions()[0].attributes('aria-current')).toBe('step')
  })

  it('loops through the views, one at a time, in step with the captions', async () => {
    mountStep()
    expect(shownViews()).toHaveLength(1)

    vi.advanceTimersByTime(2500)
    await wrapper.vm.$nextTick()
    expect(litCaption()).toBe(1)
    expect(wrapper.findAll('.wzh-frame')[1].classes()).toContain('is-shown')

    vi.advanceTimersByTime(2500 * 5)
    await wrapper.vm.$nextTick()
    expect(litCaption()).toBe(0)
    expect(shownViews()).toHaveLength(1)
  })

  it('starts another demo from its first view, at its own pace', async () => {
    mountStep()
    vi.advanceTimersByTime(5000)
    await chips()[1].trigger('click')

    expect(chips()[1].attributes('aria-pressed')).toBe('true')
    expect(captions()).toHaveLength(3)
    expect(litCaption()).toBe(0)
    expect(wrapper.find('.wzh-stage').attributes('style')).toContain('--wzh-frame-dur: 3000ms')

    vi.advanceTimersByTime(2999)
    await wrapper.vm.$nextTick()
    expect(litCaption()).toBe(0)
    vi.advanceTimersByTime(1)
    await wrapper.vm.$nextTick()
    expect(litCaption()).toBe(1)
  })

  it('pauses where it is and resumes for the rest of the view', async () => {
    mountStep()
    const control = () => wrapper.find('.wzh-demo-head > .wzh-ctrl')
    expect(control().text()).toBe('Pause')

    vi.advanceTimersByTime(1000)
    await control().trigger('click')
    expect(wrapper.find('.wzh-demo').classes()).toContain('is-paused')
    expect(control().text()).toBe('Lecture')
    vi.advanceTimersByTime(10000)
    await wrapper.vm.$nextTick()
    expect(litCaption()).toBe(0)

    await control().trigger('click')
    vi.advanceTimersByTime(1499)
    await wrapper.vm.$nextTick()
    expect(litCaption()).toBe(0)
    vi.advanceTimersByTime(1)
    await wrapper.vm.$nextTick()
    expect(litCaption()).toBe(1)
  })

  it('picking a demo while paused plays it again', async () => {
    mountStep()
    await wrapper.find('.wzh-demo-head > .wzh-ctrl').trigger('click')
    await chips()[2].trigger('click')

    expect(wrapper.find('.wzh-demo').classes()).not.toContain('is-paused')
    vi.advanceTimersByTime(3000)
    await wrapper.vm.$nextTick()
    expect(litCaption()).toBe(1)
  })

  it('with « reduce motion », stands still and steps through the views by hand', async () => {
    reduceMotion(true)
    mountStep()
    await wrapper.vm.$nextTick()

    expect(wrapper.find('.wzh-demo').classes()).toContain('is-still')
    expect(wrapper.find('.wzh-stepper').exists()).toBe(true)
    expect(wrapper.text()).not.toContain('Pause')
    const count = wrapper.find('.wzh-stepper-count')
    expect(count.attributes('aria-live')).toBe('polite')
    expect(count.text()).toBe('Vue 1 sur 6')

    vi.advanceTimersByTime(20000)
    await wrapper.vm.$nextTick()
    expect(litCaption()).toBe(0)

    const [prev, next] = wrapper.findAll('.wzh-stepper .wzh-ctrl--icon')
    expect(prev.attributes('aria-label')).toBe('Vue précédente')
    expect(next.attributes('aria-label')).toBe('Vue suivante')
    await prev.trigger('click')
    expect(count.text()).toBe('Vue 6 sur 6')
    expect(litCaption()).toBe(5)
    expect(wrapper.findAll('.wzh-frame')[5].classes()).toContain('is-shown')
    await next.trigger('click')
    expect(count.text()).toBe('Vue 1 sur 6')

    await next.trigger('click')
    await chips()[1].trigger('click')
    expect(count.text()).toBe('Vue 1 sur 3')
  })
})

describe('WizardStepHelp — reduced screens', () => {
  beforeEach(() => vi.useFakeTimers())

  it('keeps the scene out of assistive tech; the captions carry the words', () => {
    mountStep()
    expect(wrapper.find('.wzh-stage').attributes('aria-hidden')).toBe('true')
    expect(wrapper.find('.wzh-caps').element.tagName).toBe('OL')
  })

  it("draws a member's top bar, with the member's initial and no « Demandes » tab", () => {
    mountStep()
    const bar = wrapper.find('.wzh-pv-nav')
    expect(bar.findAll('.wzh-pv-tab').map(tab => tab.text())).toEqual([
      'Accueil',
      'Mon profil',
      'Problèmes',
    ])
    expect(bar.find('.wzh-pv-tab.is-on').text()).toBe('Accueil')
    expect(bar.find('.wzh-pv-avt').text()).toBe('A')
    expect(bar.find('.wzh-pv-logo').attributes('src')).toBe('/assets/icons/mk-logo-128.png')
  })

  it('shows the request flow with the real labels and the test data', () => {
    mountStep()
    const text = wrapper.text()
    expect(text).toContain('N°1 des tendances aujourd')
    expect(text).toContain('Résultats pour « Test Movie »')
    expect(text).toContain('Valider la demande')
    expect(text).toContain('Demande envoyée — 4/10 demandes ce mois')
    expect(wrapper.find('.mk-ribbon').text()).toBe('DEMANDÉ')
    const typed = wrapper.find('.wzh-typ')
    expect(typed.text()).toBe('Test Movie')
    expect(typed.attributes('style')).toContain('--wzh-chars: 10')
  })

  it('lands the cursor on the control each view presses', async () => {
    mountStep()
    const pressed = () => wrapper.findAll('.wzh-prs').map(el => el.find('.wzh-cur').exists())
    expect(pressed()).toEqual([true, true])

    await chips()[1].trigger('click')
    expect(pressed()).toEqual([true, true])
    expect(wrapper.text()).toContain('#13')

    await chips()[2].trigger('click')
    expect(pressed()).toEqual([true, true, true])
    expect(wrapper.find('.wzh-pv-tip').text()).toBe('Ajouter à une liste')
  })

  it('speaks the portal language', () => {
    mountStep('en')
    expect(chips()[0].text()).toBe('Make a request')
    expect(wrapper.find('.wzh-pv-tab.is-on').text()).toBe('Home')
    expect(wrapper.find('.mk-ribbon').text()).toBe('REQUESTED')
    expect(wrapper.find('.wzh-demo-head > .wzh-ctrl').text()).toBe('Pause')
  })
})

describe('WizardStepHelp — scale of the scene', () => {
  let resize = null

  beforeEach(() => {
    vi.useFakeTimers()
    vi.stubGlobal(
      'ResizeObserver',
      class {
        constructor(callback) {
          resize = callback
        }
        observe() {}
        disconnect() {}
      },
    )
    vi.spyOn(window, 'getComputedStyle').mockReturnValue({ getPropertyValue: () => ' 800px' })
  })

  afterEach(() => vi.restoreAllMocks())

  function boxWidth(width) {
    Object.defineProperty(wrapper.find('.wzh-stage-box').element, 'clientWidth', {
      configurable: true,
      value: width,
    })
  }

  const scale = () =>
    Number(
      wrapper
        .find('.wzh-stage')
        .attributes('style')
        .match(/--wzh-scale: ([\d.]+)/)[1],
    )

  it('fits the card, rounded down, and never grows past full size', async () => {
    vi.spyOn(Element.prototype, 'clientWidth', 'get').mockReturnValue(250)
    mountStep()
    await wrapper.vm.$nextTick()
    expect(scale()).toBe(0.312)

    boxWidth(1200)
    resize()
    await wrapper.vm.$nextTick()
    expect(scale()).toBe(1)

    boxWidth(754)
    resize()
    await wrapper.vm.$nextTick()
    expect(scale()).toBe(0.942)
  })
})
