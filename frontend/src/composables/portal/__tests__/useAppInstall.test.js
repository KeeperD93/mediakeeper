/**
 * Installing the portal as an app: the browser's offer kept from the start and its window
 * opened once, the steps to follow on iPhone, iPad, Safari on a Mac and Firefox on Android,
 * another browser for Firefox on a computer, and nothing once installed, on a page that is
 * not secure, or in another browser that cannot install.
 */
import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { INSTALL_WAY } from '@/constants/portalInstall'

const MAC = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'
const AGENT = {
  chromeAndroid:
    'Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36',
  iphone:
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1',
  safari17: `${MAC} AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15`,
  safari16: `${MAC} AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15`,
  chromeMac: `${MAC} AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36`,
  firefoxWindows:
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0',
  firefoxMac:
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:132.0) Gecko/20100101 Firefox/132.0',
  firefoxAndroid: 'Mozilla/5.0 (Android 14; Mobile; rv:132.0) Gecko/132.0 Firefox/132.0',
}

const listeners = []

/** The browser, then a fresh module: what is installed is read when the module loads. */
async function freshInstall({
  agent = AGENT.chromeAndroid,
  touch = 0,
  secure = true,
  standalone = false,
  iosStandalone = false,
  page = '/portal/lists',
} = {}) {
  vi.stubGlobal('isSecureContext', secure)
  vi.stubGlobal('navigator', {
    userAgent: agent,
    maxTouchPoints: touch,
    standalone: iosStandalone,
  })
  vi.stubGlobal('matchMedia', query => ({
    matches: standalone && query === '(display-mode: standalone)',
  }))
  window.history.replaceState(null, '', page)
  const add = vi.spyOn(window, 'addEventListener')
  vi.resetModules()
  const { listenForAppInstall, useAppInstall } = await import('@/composables/portal/useAppInstall')
  listenForAppInstall()
  listeners.push(...add.mock.calls.map(([type, handler]) => [type, handler]))
  add.mockRestore()
  return useAppInstall()
}

/** The browser's offer, its window answered with `outcome`. */
function offer(outcome = 'accepted') {
  const event = new Event('beforeinstallprompt', { cancelable: true })
  event.prompt = vi.fn(async () => {})
  event.userChoice = Promise.resolve({ outcome })
  window.dispatchEvent(event)
  return event
}

afterEach(() => {
  listeners.splice(0).forEach(([type, handler]) => window.removeEventListener(type, handler))
  vi.unstubAllGlobals()
  window.history.replaceState(null, '', '/')
})

describe('useAppInstall, the browser’s install window', () => {
  it('keeps the offer, holds the browser’s banner back on the portal, and opens the window', async () => {
    const app = await freshInstall()
    expect(app.way.value).toBeNull()

    const event = offer()
    expect(event.defaultPrevented).toBe(true)
    expect(app.way.value).toBe(INSTALL_WAY.PROMPT)
    expect(app.steps.value).toEqual([])

    await app.install()
    expect(event.prompt).toHaveBeenCalledTimes(1)
    window.dispatchEvent(new Event('appinstalled'))
    expect(app.way.value).toBeNull()
  })

  it('leaves the browser’s banner alone outside the portal, offer kept', async () => {
    const app = await freshInstall({ page: '/login' })

    const event = offer()
    expect(event.defaultPrevented).toBe(false)
    expect(app.way.value).toBe(INSTALL_WAY.PROMPT)
  })

  it('offers it no more during the visit once refused in the browser’s window', async () => {
    const app = await freshInstall()
    offer('dismissed')

    await app.install()
    expect(app.way.value).toBeNull()
    // The browser may offer again at once: the portal stays quiet until the next visit.
    offer()
    expect(app.way.value).toBeNull()
  })

  it('opens the window once, even clicked twice', async () => {
    const app = await freshInstall()
    const event = offer()

    await Promise.all([app.install(), app.install()])
    expect(event.prompt).toHaveBeenCalledTimes(1)
  })

  it('drops the button when the browser will not open its window', async () => {
    const app = await freshInstall()
    const event = offer()
    event.prompt.mockRejectedValue(new DOMException('Not allowed', 'NotAllowedError'))

    await app.install()
    await flushPromises()
    expect(app.way.value).toBeNull()
  })
})

describe('useAppInstall, the steps to follow', () => {
  it('on an iPhone: Share, then « Add to Home Screen », and the notifications it brings', async () => {
    const app = await freshInstall({ agent: AGENT.iphone })

    expect(app.way.value).toBe(INSTALL_WAY.IOS)
    expect(app.steps.value).toEqual(['portal.appInstall.ios', 'portal.appInstall.iosNotify'])
  })

  it('on an iPad, which says it is a Mac with a touch screen', async () => {
    const app = await freshInstall({ agent: AGENT.safari17, touch: 5 })
    expect(app.way.value).toBe(INSTALL_WAY.IOS)
  })

  it('in Safari 17 on a Mac: File, then « Add to Dock »', async () => {
    const app = await freshInstall({ agent: AGENT.safari17 })

    expect(app.way.value).toBe(INSTALL_WAY.MAC)
    expect(app.steps.value).toEqual(['portal.appInstall.mac'])
  })

  it('in Firefox on Android: its menu, then « Add app to Home screen »', async () => {
    const app = await freshInstall({ agent: AGENT.firefoxAndroid })

    expect(app.way.value).toBe(INSTALL_WAY.FIREFOX_ANDROID)
    expect(app.steps.value).toEqual(['portal.appInstall.firefoxAndroid'])
  })

  it.each([
    ['Windows', AGENT.firefoxWindows],
    ['a Mac, no Safari steps', AGENT.firefoxMac],
  ])('in Firefox on %s: another browser to install it', async (_, agent) => {
    const app = await freshInstall({ agent })

    expect(app.way.value).toBe(INSTALL_WAY.OTHER_BROWSER)
    expect(app.steps.value).toEqual(['portal.appInstall.otherBrowser'])
  })
})

describe('useAppInstall, nothing to offer', () => {
  it.each([
    ['Safari before 17 on a Mac', AGENT.safari16],
    ['Chrome on a Mac that sent no offer', AGENT.chromeMac],
  ])('in %s', async (_, agent) => {
    const app = await freshInstall({ agent })
    expect(app.way.value).toBeNull()
    expect(app.steps.value).toEqual([])
  })

  it('once installed, opened from its icon', async () => {
    const app = await freshInstall({ standalone: true })
    offer()
    expect(app.way.value).toBeNull()
  })

  it('on an iPhone, opened from the home screen', async () => {
    const app = await freshInstall({ agent: AGENT.iphone, iosStandalone: true })
    expect(app.way.value).toBeNull()
  })

  it.each([
    ['an offer', AGENT.chromeAndroid],
    ['an iPhone', AGENT.iphone],
    ['Firefox', AGENT.firefoxWindows],
  ])('on a page that is not secure, even with %s', async (_, agent) => {
    const app = await freshInstall({ agent, secure: false })
    offer()
    expect(app.way.value).toBeNull()
  })
})
