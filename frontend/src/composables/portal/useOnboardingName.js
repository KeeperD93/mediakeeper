/**
 * The name step of the first-login wizard: what the field holds, the server's verdict
 * on it, the message under it and the main button's words. Nothing is ruled here:
 * every verdict comes from the server's live check (or from the save that refused).
 */
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { DISPLAY_NAME_REASON } from '@/constants/displayName'
import { NAME_CHECK_FAILED, WIZARD_ACCOUNT } from '@/constants/portalOnboarding'
import { useDisplayNameCheck } from '@/composables/portal/useDisplayNameCheck'
import { localizedDate } from '@/utils/datetime'
import { daysUntil } from '@/utils/portal/onboarding'

const K = 'portal.wizard.name'
const ACCEPTED = [DISPLAY_NAME_REASON.CURRENT, DISPLAY_NAME_REASON.FREE]
// The save's refusals that need the check's extras: the free names, the days left.
const RECHECKED = [DISPLAY_NAME_REASON.TAKEN, DISPLAY_NAME_REASON.LOCKED]
const LONG_DATE = { day: 'numeric', month: 'long', year: 'numeric' }

/**
 * @param {object} options
 * @param {import('vue').Ref<string>} options.account a WIZARD_ACCOUNT, LOCKED once known
 * @param {import('vue').Ref<string|null>} options.lockedUntil end of the lock of a LOCKED account
 * @param {import('vue').Ref<boolean>} options.lockPending true until the lock is known
 * @param {string} options.current the name the account has now
 * @param {boolean} options.reset the name alone, after an admin reset it
 */
export function useOnboardingName({ account, lockedUntil, lockPending, current, reset }) {
  const { t } = useI18n()
  const { state: check, check: runCheck, refuse: showRefusal } = useDisplayNameCheck()
  // A name still owed starts empty: neither the provisional nor the reset one can be kept.
  const owed = [WIZARD_ACCOUNT.NEW, WIZARD_ACCOUNT.RESET].includes(account.value)
  const value = ref(owed ? '' : current)
  const touched = ref(false)
  const locked = computed(() => account.value === WIZARD_ACCOUNT.LOCKED)
  const frozen = computed(() => locked.value || lockPending.value)
  const trimmed = computed(() => value.value.trim())

  // 'empty', 'pending', a DISPLAY_NAME_REASON or NAME_CHECK_FAILED.
  const verdict = computed(() => {
    if (!trimmed.value) return 'empty'
    if (check.pending) return 'pending'
    return check.reason
  })
  const ok = computed(
    () => !lockPending.value && (locked.value || ACCEPTED.includes(verdict.value)),
  )
  const refused = computed(
    () =>
      !ACCEPTED.includes(verdict.value) &&
      Object.values(DISPLAY_NAME_REASON).includes(verdict.value),
  )
  const invalid = computed(
    () => !frozen.value && (refused.value || (touched.value && verdict.value === 'empty')),
  )

  /** `{ tone: 'ok' | 'err' | 'info', text }` under the field. */
  const message = computed(() => {
    if (lockPending.value) return { tone: 'info', text: t(`${K}.checking`) }
    if (locked.value) {
      return { tone: 'info', text: t(`${K}.lockedAccount`, { date: dateOf(lockedUntil.value) }) }
    }
    const v = verdict.value
    if (v === 'empty') {
      if (touched.value) return { tone: 'err', text: t(`${K}.empty`) }
      return { tone: 'info', text: owed || reset ? t(`${K}.prompt`) : '' }
    }
    if (v === 'pending') return { tone: 'info', text: t(`${K}.checking`) }
    if (v === NAME_CHECK_FAILED) return { tone: 'err', text: t(`${K}.checkFailed`) }
    if (v === DISPLAY_NAME_REASON.LOCKED) {
      const days = daysUntil(check.lockedUntil)
      return { tone: 'err', text: t(`${K}.reason.locked`, { n: days }, days) }
    }
    if (v === DISPLAY_NAME_REASON.FREE) return { tone: 'ok', text: t(`${K}.reason.free`) }
    if (v === DISPLAY_NAME_REASON.CURRENT) return { tone: 'info', text: t(`${K}.reason.current`) }
    return { tone: 'err', text: t(`${K}.reason.${v}`) }
  })

  const suggestions = computed(() =>
    verdict.value === DISPLAY_NAME_REASON.TAKEN ? check.suggestions : [],
  )

  const buttonLabel = computed(() => {
    if (reset) return t('portal.wizard.actions.confirmReset')
    if (locked.value) return t('portal.wizard.actions.next')
    if (verdict.value === DISPLAY_NAME_REASON.CURRENT) return t('portal.wizard.actions.keep')
    return t('portal.wizard.actions.confirm')
  })

  /** The name the wizard keeps: the one typed once accepted, else the account's. */
  const shown = computed(() => (!locked.value && ok.value && trimmed.value) || current)

  function input(next) {
    value.value = next
    touched.value = true
    runCheck(next)
  }

  function retry() {
    runCheck(value.value)
  }

  /** The save refused the name for `reason` (taken meanwhile…). */
  function refusedBySave(reason) {
    touched.value = true
    if (RECHECKED.includes(reason)) runCheck(value.value)
    else showRefusal(trimmed.value, reason)
  }

  function dateOf(iso) {
    return iso ? localizedDate(iso, LONG_DATE) : ''
  }

  // A lock learnt once the wizard is open: the field shows the account's name again.
  watch(locked, isLocked => {
    if (isLocked) value.value = current
  })

  // A name already filled in (an existing account) is judged before the step shows.
  if (!owed) runCheck(value.value)

  return {
    value,
    trimmed,
    touched,
    locked,
    frozen,
    ok,
    invalid,
    message,
    suggestions,
    buttonLabel,
    shown,
    failed: computed(() => verdict.value === NAME_CHECK_FAILED),
    free: computed(() => verdict.value === DISPLAY_NAME_REASON.FREE),
    input,
    retry,
    refusedBySave,
  }
}
