/**
 * First-login wizard, « where to find »: the desktop drawing is the help demos' top bar,
 * with the member's initial and the ring of their tier; the phone's draws no « + »
 * button, its legend names it. Fictional member « Alice ».
 */
import { afterEach, describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import i18n from '@/i18n'
import WizardNavMap from '@/components/portal/wizard/WizardNavMap.vue'
import { ONBOARDING_WIZARD_KEY } from '@/composables/portal/useOnboardingWizard'

let wrapper

function mountMap(tier) {
  i18n.global.locale.value = 'fr'
  wrapper = mount(WizardNavMap, {
    global: {
      plugins: [i18n],
      mocks: { $t: i18n.global.t },
      provide: { [ONBOARDING_WIZARD_KEY]: { initial: 'A', me: { tier } } },
    },
  })
}

afterEach(() => wrapper?.unmount())

describe('WizardNavMap', () => {
  it('draws the demos’ top bar, home lit, with the member’s initial and tier', () => {
    mountMap('gold')

    const bar = wrapper.get('.wz-nm .wzh-pv-nav')
    expect(bar.get('.wzh-pv-tab.is-on').text()).toBe('Accueil')
    expect(bar.get('.wzh-pv-avt').text()).toBe('A')
    expect(bar.get('.wz-av').classes()).toContain('wz-av--gold')
    expect(wrapper.findAll('.wzh-pv-nav')).toHaveLength(1)
  })

  it('draws no « + » button on the phone: the legend tells where it is, as on a computer', () => {
    mountMap('bronze')

    const drawn = [...wrapper.get('.wz-mphone').element.children].map(el => el.className)
    const legend = side => wrapper.findAll(`.wz-map-${side} .wz-mlegend li`).map(li => li.text())
    expect(drawn).toEqual(['wz-mbar', 'wz-mbottom'])
    expect(legend('phone').at(-1)).toBe(legend('desk').at(-1))
    expect(legend('phone').at(-1)).toContain('+')
  })

  it('shows the same logo on the desktop bar and on the phone', () => {
    mountMap('bronze')

    const logos = wrapper.findAll('img').map(img => img.attributes('src'))
    expect(logos).toEqual(['/assets/icons/mk-logo-128.png', '/assets/icons/mk-logo-128.png'])
  })
})
