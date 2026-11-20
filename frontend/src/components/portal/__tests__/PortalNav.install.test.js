/**
 * The avatar menu's « Install the app » line: right above « Log out » where the browser
 * can install the portal, absent elsewhere. It opens the browser's own window, or the
 * steps to follow, the focus going back to the avatar once they close.
 */
import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { nextTick, ref } from 'vue'

import PortalNav from '@/components/portal/PortalNav.vue'
import { INSTALL_WAY } from '@/constants/portalInstall'

const browser = vi.hoisted(() => ({ way: null, steps: [], install: vi.fn() }))

vi.mock('vue-router', () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    currentRoute: ref({ fullPath: '/portal' }),
  }),
}))
vi.mock('vue-i18n', async importOriginal => ({
  ...(await importOriginal()),
  useI18n: () => ({ t: key => key }),
}))
vi.mock('@/composables/useAuth', () => ({ useAuth: () => ({ logout: vi.fn() }) }))
vi.mock('@/composables/portal/useSearchHotkey', () => ({ useSearchHotkey: vi.fn() }))
vi.mock('@/composables/portal/usePortalAuth', () => ({ usePortalAuth: () => ({ ui: ref({}) }) }))
vi.mock('@/composables/portal/useAppInstall', () => ({
  useAppInstall: () => ({
    way: ref(browser.way),
    steps: ref(browser.steps),
    install: browser.install,
  }),
}))

let wrapper

async function openMenu(way, steps = []) {
  Object.assign(browser, { way, steps })
  browser.install.mockClear()
  wrapper = mount(PortalNav, {
    props: { profile: { display_name: 'Alice' } },
    attachTo: document.body,
    global: {
      stubs: {
        NotificationBell: true,
        CalendarButton: true,
        PortalSearchBox: true,
        MkAvatar: true,
        DonationOverlay: true,
        FeedbackModal: true,
      },
    },
  })
  await wrapper.get('.pt-avatar-trigger').trigger('click')
  return wrapper
}
const items = () => wrapper.findAll('.pt-avatar-pop-item').map(item => item.text())
const installItem = () =>
  wrapper.findAll('.pt-avatar-pop-item').find(item => item.text() === 'portal.appInstall.title')

afterEach(() => wrapper?.unmount())

describe('PortalNav.vue, installing the app from the avatar menu', () => {
  it('sits right above « Log out » where the browser can install', async () => {
    await openMenu(INSTALL_WAY.PROMPT)

    const lines = items()
    expect(lines.at(-1)).toBe('portal.avatar.logout')
    expect(lines.at(-2)).toBe('portal.appInstall.title')
  })

  it('is absent where the browser cannot install', async () => {
    await openMenu(null)
    expect(items()).not.toContain('portal.appInstall.title')
  })

  it('opens the browser’s window at once, the menu closed', async () => {
    await openMenu(INSTALL_WAY.PROMPT)

    await installItem().trigger('click')

    expect(browser.install).toHaveBeenCalledTimes(1)
    expect(wrapper.find('.pt-avatar-pop').exists()).toBe(false)
    expect(wrapper.find('.pis-panel').exists()).toBe(false)
  })

  it('opens the steps elsewhere, then gives the focus back to the avatar', async () => {
    await openMenu(INSTALL_WAY.OTHER_BROWSER, ['portal.appInstall.otherBrowser'])

    await installItem().trigger('click')
    await nextTick()

    expect(browser.install).not.toHaveBeenCalled()
    expect(wrapper.find('.pt-avatar-pop').exists()).toBe(false)
    expect(wrapper.findAll('.pis-text').map(text => text.text())).toEqual([
      'portal.appInstall.intro',
      'portal.appInstall.otherBrowser',
    ])
    expect(document.activeElement).toBe(wrapper.get('.pis-close').element)

    await wrapper.get('.pis-close').trigger('click')
    await flushPromises()
    expect(wrapper.find('.pis-panel').exists()).toBe(false)
    expect(document.activeElement).toBe(wrapper.get('.pt-avatar-trigger').element)
  })
})
