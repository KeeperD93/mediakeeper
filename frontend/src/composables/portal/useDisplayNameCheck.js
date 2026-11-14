/**
 * The server's live verdict on a display name being typed. The server alone judges
 * (length, look-alikes, reserved, taken…): one request after a pause in typing, an
 * answer about an older text ignored, a check that got no answer said as such.
 */
import { onScopeDispose, reactive } from 'vue'
import { useApi } from '@/composables/useApi'
import {
  NAME_CHECK_DEBOUNCE_MS,
  NAME_CHECK_FAILED,
  NAME_SUGGESTIONS_SHOWN,
} from '@/constants/portalOnboarding'

export function useDisplayNameCheck() {
  const { apiGet } = useApi()
  const state = reactive({
    name: '',
    pending: false,
    // A DISPLAY_NAME_REASON, NAME_CHECK_FAILED, or null before any verdict.
    reason: null,
    lockedUntil: null,
    suggestions: [],
  })
  let timer = null
  let ticket = 0

  function settle(name, fields = {}) {
    clearTimeout(timer)
    ticket += 1
    Object.assign(state, {
      name,
      pending: false,
      reason: null,
      lockedUntil: null,
      suggestions: [],
      ...fields,
    })
    return ticket
  }

  function check(raw) {
    const name = (raw || '').trim()
    if (!name) {
      settle('')
      return
    }
    const mine = settle(name, { pending: true })
    timer = setTimeout(async () => {
      try {
        const res = await apiGet(
          `/api/portal/profiles/me/check-username?name=${encodeURIComponent(name)}`,
        )
        if (mine !== ticket) return
        state.reason = res?.reason || NAME_CHECK_FAILED
        state.lockedUntil = res?.locked_until || null
        state.suggestions = (res?.suggestions || []).slice(0, NAME_SUGGESTIONS_SHOWN)
      } catch {
        if (mine === ticket) state.reason = NAME_CHECK_FAILED
      } finally {
        if (mine === ticket) state.pending = false
      }
    }, NAME_CHECK_DEBOUNCE_MS)
  }

  /** The save refused `name` for `reason`: show that verdict, as a check would. */
  function refuse(name, reason) {
    settle(name, { reason })
  }

  onScopeDispose(() => clearTimeout(timer))

  return { state, check, refuse }
}
