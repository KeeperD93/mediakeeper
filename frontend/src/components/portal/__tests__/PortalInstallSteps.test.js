/**
 * The steps to install the app, opened from the avatar menu where the browser has no
 * install window: the same texts as at the end of the first-login wizard, and every way
 * out (its button, Escape, a click beside it) closes it.
 */
import { afterEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { ref } from 'vue'

import PortalInstallSteps from '@/components/portal/PortalInstallSteps.vue'

vi.mock('@/composables/portal/useAppInstall', () => ({
  useAppInstall: () => ({
    steps: ref(['portal.appInstall.ios', 'portal.appInstall.iosNotify']),
  }),
}))

let wrapper
const mountSteps = open => {
  wrapper = mount(PortalInstallSteps, { props: { open }, attachTo: document.body })
  return wrapper
}

afterEach(() => wrapper?.unmount())

describe('PortalInstallSteps.vue', () => {
  it('shows the title, what it brings and the steps for this browser', () => {
    mountSteps(true)

    expect(wrapper.find('.pis-title').text()).toBe('portal.appInstall.title')
    expect(wrapper.findAll('.pis-text').map(text => text.text())).toEqual([
      'portal.appInstall.intro',
      'portal.appInstall.ios',
      'portal.appInstall.iosNotify',
    ])
  })

  it('shows nothing while closed', () => {
    mountSteps(false)
    expect(wrapper.find('[role="dialog"]').exists()).toBe(false)
  })

  it('closes from its button, from Escape and from a click beside it', async () => {
    mountSteps(true)

    await wrapper.get('.pis-close').trigger('click')
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))
    await wrapper.get('.pis-overlay').trigger('click')
    // A click on the window itself is no way out.
    await wrapper.get('.pis-panel').trigger('click')

    expect(wrapper.emitted('close')).toHaveLength(3)
  })
})
