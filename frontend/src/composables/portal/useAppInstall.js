/**
 * Installing the portal as an app. Chrome, Edge and Android open their own install window;
 * where there is none, the portal shows the steps to follow, or another browser to use.
 * Nothing is stored: the browser knows whether the app is installed.
 */
import { computed, ref, shallowRef } from 'vue'
import { INSTALL_WAY } from '@/constants/portalInstall'

// Safari adds a site to the Dock from this version on (macOS Sonoma).
const SAFARI_DOCK_VERSION = 17
const PORTAL_PAGE = /^\/portal(\/|$)/
const STEP_KEYS = {
  [INSTALL_WAY.IOS]: ['portal.appInstall.ios', 'portal.appInstall.iosNotify'],
  [INSTALL_WAY.MAC]: ['portal.appInstall.mac'],
  [INSTALL_WAY.FIREFOX_ANDROID]: ['portal.appInstall.firefoxAndroid'],
  [INSTALL_WAY.OTHER_BROWSER]: ['portal.appInstall.otherBrowser'],
}

function runsAsApp() {
  // jsdom (unit tests) has no matchMedia.
  const standalone =
    typeof window.matchMedia === 'function' &&
    window.matchMedia('(display-mode: standalone)').matches
  // iPhone and iPad tell it their own way.
  return standalone || navigator.standalone === true
}

// The browser's offer often comes before the portal shows anything: it is kept from the
// app's start (listenForAppInstall, called by main.js).
const offer = shallowRef(null)
// Refused in the browser's window: the portal does not offer it again before the next visit.
const declined = ref(false)
const installed = ref(runsAsApp())

/**
 * Browsers without an install window: iPhone and iPad (an iPad says it is a Mac, with a
 * touch screen), Firefox, Safari on a Mac.
 */
function textWay() {
  const agent = navigator.userAgent
  const mac = /Macintosh/.test(agent)
  if (/iPhone|iPad|iPod/.test(agent) || (mac && navigator.maxTouchPoints > 1)) {
    return INSTALL_WAY.IOS
  }
  // Firefox installs from its menu on Android; on a computer, only behind a test setting.
  if (/Firefox\//.test(agent)) {
    return /Android/.test(agent) ? INSTALL_WAY.FIREFOX_ANDROID : INSTALL_WAY.OTHER_BROWSER
  }
  const safari = /Version\/(\d+)[\d.]* Safari\//.exec(agent)
  return mac && safari && Number(safari[1]) >= SAFARI_DOCK_VERSION ? INSTALL_WAY.MAC : null
}

/** Called once, before the app mounts: the offer may come before any portal page. */
export function listenForAppInstall() {
  window.addEventListener('beforeinstallprompt', event => {
    // The portal offers the install itself: no browser banner over its pages.
    if (PORTAL_PAGE.test(window.location.pathname)) event.preventDefault()
    offer.value = event
  })
  window.addEventListener('appinstalled', () => {
    installed.value = true
    offer.value = null
  })
}

export function useAppInstall() {
  // Nothing on a page that is not secure (https, or the local machine): Chrome and Edge do
  // not offer it there, and the app it would make could not show notifications.
  const way = computed(() => {
    if (installed.value || !window.isSecureContext) return null
    if (offer.value && !declined.value) return INSTALL_WAY.PROMPT
    return textWay()
  })
  const steps = computed(() => STEP_KEYS[way.value] || [])

  /** Opens the browser's install window: an offer serves once. */
  async function install() {
    const event = offer.value
    // A second click before the button went away.
    if (!event) return
    offer.value = null
    try {
      await event.prompt()
      const { outcome } = await event.userChoice
      if (outcome === 'dismissed') declined.value = true
    } catch {
      // The browser would not open its window: the button is gone with the offer.
    }
  }

  return { way, steps, install }
}
