/**
 * Whether this browser may show the portal's notifications, and the request for it.
 * Nothing is stored on the server: the permission lives in the browser.
 */
import { ref } from 'vue'
import { NOTIFY_STATE } from '@/constants/portalOnboarding'

function readState() {
  // Browsers only offer notifications to secure pages (https, or the local machine).
  if (!window.isSecureContext) return NOTIFY_STATE.INSECURE
  // iPhone and iPad offer them only to a portal added to the home screen.
  if (!('Notification' in window)) return NOTIFY_STATE.UNSUPPORTED
  return Notification.permission
}

export function useBrowserNotifications() {
  const state = ref(readState())

  /** Open the browser's own question; resolves once the person answered or closed it. */
  async function request() {
    try {
      await Notification.requestPermission()
    } catch {
      // A browser that refuses to ask leaves the permission as it was.
    }
    // Read back rather than trust the result: older Safari answers through a callback.
    state.value = readState()
    return state.value
  }

  return { state, request }
}
