/**
 * The install steps and the keyboard: the focus starts on « Close », Tab and Shift+Tab
 * stay inside the window, and closing it gives the focus back to what had it before.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick, ref } from 'vue'

import PortalInstallSteps from '@/components/portal/PortalInstallSteps.vue'

vi.mock('@/composables/portal/useAppInstall', () => ({
  useAppInstall: () => ({ steps: ref(['portal.appInstall.mac']) }),
}))

let wrapper
let opener

const press = (key, shiftKey = false) =>
  document.dispatchEvent(new KeyboardEvent('keydown', { key, shiftKey, bubbles: true }))

async function open() {
  wrapper = mount(PortalInstallSteps, { props: { open: false }, attachTo: document.body })
  await wrapper.setProps({ open: true })
  await nextTick()
}

describe('PortalInstallSteps.vue, focus trap', () => {
  beforeEach(() => {
    opener = document.createElement('button')
    opener.textContent = 'Open'
    document.body.append(opener)
    opener.focus()
  })
  afterEach(() => {
    wrapper?.unmount()
    opener.remove()
  })

  it('starts on « Close », in a dialog named by its title', async () => {
    await open()

    expect(document.activeElement).toBe(wrapper.get('.pis-close').element)
    const dialog = wrapper.get('[role="dialog"]')
    expect(dialog.attributes('aria-modal')).toBe('true')
    const title = document.getElementById(dialog.attributes('aria-labelledby'))
    expect(title.textContent).toBe('portal.appInstall.title')
  })

  it('keeps Tab and Shift+Tab inside the window', async () => {
    await open()
    const close = wrapper.get('.pis-close').element

    press('Tab')
    expect(document.activeElement).toBe(close)
    press('Tab', true)
    expect(document.activeElement).toBe(close)
  })

  it('gives the focus back once closed', async () => {
    await open()

    await wrapper.setProps({ open: false })
    await nextTick()
    expect(document.activeElement).toBe(opener)
  })
})
