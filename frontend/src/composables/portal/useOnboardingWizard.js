/**
 * The first-login wizard's state, shared with its steps (provide/inject): the steps,
 * the choices kept in memory until the end, the moves between steps and the texts of
 * each step's head. Nothing is written before the last button (see useOnboardingSave).
 */
import { computed, onScopeDispose, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  AVATAR_CHOICE,
  AVATAR_EXTENSIONS,
  AVATAR_MAX_BYTES,
  AVATAR_TYPES,
  FULL_TOUR,
  MAX_FAVORITE_GENRES,
  NOTIFY_STATE,
  WIZARD_ACCOUNT,
  WIZARD_MODE,
  WIZARD_STEP as S,
} from '@/constants/portalOnboarding'
import { useApi } from '@/composables/useApi'
import { useBrowserNotifications } from '@/composables/portal/useBrowserNotifications'
import { useOnboardingName } from '@/composables/portal/useOnboardingName'
import { useOnboardingSave } from '@/composables/portal/useOnboardingSave'
import { usePortalAuth } from '@/composables/portal/usePortalAuth'
import { usePortalLocale } from '@/composables/portal/usePortalLocale'
import { avatarFileProblem, initialOf } from '@/utils/portal/onboarding'

export const ONBOARDING_WIZARD_KEY = Symbol('onboarding-wizard')
// Id of the step's title, which names the step's groups of choices.
export const ONBOARDING_HEADING_KEY = Symbol('onboarding-heading')

const W = 'portal.wizard'
// Notifications that need no « are you sure? »: on, or impossible here.
const NOTIFY_SETTLED = [NOTIFY_STATE.GRANTED, NOTIFY_STATE.INSECURE, NOTIFY_STATE.UNSUPPORTED]
// The name step's subtitle, by account (a reset one reads as the reset alone does).
const NAME_SUB = {
  [WIZARD_ACCOUNT.NEW]: 'subNew',
  [WIZARD_ACCOUNT.EXISTING]: 'subExisting',
  [WIZARD_ACCOUNT.LOCKED]: 'subLocked',
}

// A name still owed was never chosen, or chosen then reset: the server tells them apart
// by the date of the last choice, which a reset keeps.
function firstAccount(profile) {
  if (!profile.display_name_must_set) return WIZARD_ACCOUNT.EXISTING
  return profile.display_name_changed_at ? WIZARD_ACCOUNT.RESET : WIZARD_ACCOUNT.NEW
}

export function useOnboardingWizard(mode, onDone) {
  const { t } = useI18n()
  const { apiGet } = useApi()
  const { profile } = usePortalAuth()
  const { applyPortalLocale } = usePortalLocale()
  // The profile as the wizard opened: later saves must not reshape the steps.
  const me = { ...profile.value }
  const full = mode === WIZARD_MODE.FULL
  const steps = full ? FULL_TOUR : [S.NAME]
  const counted = steps.filter(step => step !== S.WELCOME && step !== S.DONE)
  const index = ref(0)
  const step = computed(() => steps[index.value])

  const account = ref(firstAccount(me))
  const lockedUntil = ref(null)
  // An existing name may be locked: nothing is offered on it until the server says.
  const lockPending = ref(full && account.value === WIZARD_ACCOUNT.EXISTING)
  // The instance's own language is only known while the account follows it.
  const instanceLanguage = me.language ? null : me.effective_language || null

  const choices = reactive({
    language: me.language ?? null,
    isPublic: !!me.forced_public || me.is_public !== false,
    genres: [...new Set(me.favorite_genres || [])],
    avatar: AVATAR_CHOICE.KEEP,
    avatarFile: null,
    avatarPreview: null,
    avatarProblem: null,
  })

  const name = useOnboardingName({
    account,
    lockedUntil,
    lockPending,
    current: me.display_name || '',
    reset: !full,
  })
  const notify = useBrowserNotifications()
  const notifyConfirm = ref(false)

  const save = useOnboardingSave({
    payload: () => ({
      display_name: name.locked.value ? me.display_name : name.trimmed.value,
      language: choices.language,
      is_public: choices.isPublic,
      favorite_genres: choices.genres.slice(0, MAX_FAVORITE_GENRES),
    }),
    avatarFile: () => (choices.avatar === AVATAR_CHOICE.OWN ? choices.avatarFile : null),
    onNameRefused: reason => {
      // A locked name the rules refused since the wizard opened: the field opens to say
      // why, or the person could neither keep it nor pick another.
      if (name.locked.value) account.value = WIZARD_ACCOUNT.EXISTING
      name.refusedBySave(reason)
      goTo(S.NAME)
    },
    onDone,
  })

  if (lockPending.value) {
    apiGet('/api/portal/profiles/me/username-state')
      .then(res => {
        if (!res?.locked) return
        lockedUntil.value = res.locked_until
        account.value = WIZARD_ACCOUNT.LOCKED
      })
      // Unknown lock: the field opens and the live check answers `locked`.
      .catch(() => {})
      .finally(() => {
        lockPending.value = false
      })
  }

  // The name alone after a reset is no tour: no progress to show.
  const progress = computed(() => {
    const num = counted.indexOf(step.value) + 1
    return full && num ? { num, total: counted.length } : null
  })

  const initial = computed(() => initialOf(name.shown.value))
  const avatarSrc = computed(() =>
    choices.avatar === AVATAR_CHOICE.OWN && choices.avatarPreview
      ? choices.avatarPreview
      : me.avatar_url || null,
  )

  function goTo(target) {
    index.value = steps.indexOf(target)
  }

  function back() {
    index.value -= 1
  }

  // « Next » on notifications not turned on: an « are you sure? » first, inside the step.
  function notifyNeedsConfirm() {
    if (NOTIFY_SETTLED.includes(notify.state.value) || notifyConfirm.value) return false
    notifyConfirm.value = true
    return true
  }

  async function askNotifications() {
    notifyConfirm.value = (await notify.request()) !== NOTIFY_STATE.GRANTED
  }

  function next() {
    if (step.value === S.NAME && !name.ok.value) {
      name.touched.value = true
      return
    }
    if (!full) return save.saveName()
    if (step.value === S.DONE) return save.saveAll()
    if (step.value === S.NOTIFICATIONS && notifyNeedsConfirm()) return
    index.value += 1
  }

  // The portal speaks the chosen language as soon as its step is left (nothing saved yet).
  watch(step, (now, before) => {
    if (now === S.NOTIFICATIONS) notifyConfirm.value = false
    if (before !== S.LANGUAGE) return
    const language = choices.language ?? instanceLanguage
    if (language) applyPortalLocale(language)
  })

  function pickAvatar(file) {
    choices.avatarProblem = avatarFileProblem(file, {
      types: AVATAR_TYPES,
      extensions: AVATAR_EXTENSIONS,
      maxBytes: AVATAR_MAX_BYTES,
    })
    if (choices.avatarProblem) return
    if (choices.avatarPreview) URL.revokeObjectURL(choices.avatarPreview)
    choices.avatarFile = file
    choices.avatarPreview = URL.createObjectURL(file)
  }

  function chooseAvatar(choice) {
    choices.avatar = choice
    choices.avatarProblem = null
  }

  onScopeDispose(() => {
    if (choices.avatarPreview) URL.revokeObjectURL(choices.avatarPreview)
  })

  const resetSub = () => t(`${W}.steps.reset.sub`, { name: me.display_name || '' })
  const nameSub = () =>
    account.value === WIZARD_ACCOUNT.RESET
      ? resetSub()
      : t(`${W}.steps.name.${NAME_SUB[account.value]}`)

  // Eyebrow, title and subtitle of the step's head; the welcome goes without an eyebrow.
  const head = computed(() => {
    const key = `${W}.steps.${step.value}`
    if (step.value === S.WELCOME) {
      const fresh = account.value === WIZARD_ACCOUNT.NEW
      return { title: t(`${key}.title`), sub: t(`${key}.${fresh ? 'subNew' : 'sub'}`) }
    }
    if (!full) {
      return {
        eyebrow: t(`${W}.steps.reset.eyebrow`),
        title: t(`${W}.steps.reset.title`),
        sub: resetSub(),
      }
    }
    return {
      eyebrow: t(`${key}.eyebrow`),
      title: t(`${key}.title`, { name: name.shown.value }),
      sub: step.value === S.NAME ? nameSub() : t(`${key}.sub`),
    }
  })

  const nextLabel = computed(() => {
    if (save.saving.value) return t(`${W}.actions.saving`)
    if (step.value === S.WELCOME) return t(`${W}.actions.start`)
    if (step.value === S.NAME) return name.buttonLabel.value
    if (step.value === S.DONE) return t(`${W}.actions.finish`)
    if (step.value === counted.at(-1)) return t(`${W}.actions.last`)
    return t(`${W}.actions.next`)
  })

  const footHint = computed(() => {
    if (step.value === S.WELCOME) return t(`${W}.footHint.welcome`)
    if (!full && !name.ok.value) return t(`${W}.footHint.required`)
    return ''
  })

  return reactive({
    me,
    full,
    steps,
    step,
    progress,
    account,
    choices,
    instanceLanguage,
    name,
    notify: { state: notify.state, confirm: notifyConfirm, ask: askNotifications },
    initial,
    avatarSrc,
    head,
    nextLabel,
    footHint,
    canBack: computed(() => full && index.value > 0 && !save.saving.value),
    canNext: computed(() => !save.saving.value && (step.value !== S.NAME || name.ok.value)),
    saving: save.saving,
    saveFailed: save.failed,
    next,
    back,
    goTo,
    leaveNotifications: () => {
      index.value += 1
    },
    pickAvatar,
    chooseAvatar,
  })
}
