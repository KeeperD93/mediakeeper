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
// The name step's subtitle, by account.
const NAME_SUB = {
  [WIZARD_ACCOUNT.NEW]: 'subNew',
  [WIZARD_ACCOUNT.EXISTING]: 'subExisting',
  [WIZARD_ACCOUNT.LOCKED]: 'subLocked',
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

  const account = ref(me.display_name_must_set ? WIZARD_ACCOUNT.NEW : WIZARD_ACCOUNT.EXISTING)
  const lockedUntil = ref(null)
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
      name.refusedBySave(reason)
      goTo(S.NAME)
    },
    onDone,
  })

  if (full && account.value === WIZARD_ACCOUNT.EXISTING) {
    apiGet('/api/portal/profiles/me/username-state')
      .then(res => {
        if (!res?.locked) return
        lockedUntil.value = res.locked_until
        account.value = WIZARD_ACCOUNT.LOCKED
      })
      // Unknown lock: the field stays open and the live check answers `locked`.
      .catch(() => {})
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

  // Eyebrow, title and subtitle of the step's head.
  const head = computed(() => {
    const key = `${W}.steps.${step.value}`
    const fresh = account.value === WIZARD_ACCOUNT.NEW
    if (step.value === S.WELCOME) {
      return {
        eyebrow: t(`${key}.${fresh ? 'eyebrowNew' : 'eyebrow'}`),
        title: t(`${key}.title`),
        sub: t(`${key}.${fresh ? 'subNew' : 'sub'}`),
      }
    }
    if (!full) {
      return {
        eyebrow: t(`${W}.steps.reset.eyebrow`),
        title: t(`${W}.steps.reset.title`),
        sub: t(`${W}.steps.reset.sub`, { name: me.display_name || '' }),
      }
    }
    const sub = step.value === S.NAME ? NAME_SUB[account.value] : 'sub'
    return {
      eyebrow: t(`${key}.eyebrow`),
      title: t(`${key}.title`, { name: name.shown.value }),
      sub: t(`${key}.${sub}`),
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
