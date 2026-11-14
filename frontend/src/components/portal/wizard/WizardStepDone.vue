<template>
  <div class="dd-box wz-recap">
    <div v-for="row in rows" :key="row.step" class="wz-rrow">
      <div class="dd-grow">
        <span class="wz-rl">{{ $t(`portal.wizard.done.rows.${row.step}`) }}</span>
        <span class="wz-rv">{{ row.value }}</span>
      </div>
      <button
        v-if="row.editable"
        type="button"
        class="wz-link"
        :aria-label="$t(`portal.wizard.done.edit.${row.step}`)"
        :disabled="wz.saving"
        @click="wz.goTo(row.step)"
      >
        {{ $t('portal.wizard.done.editText') }}
      </button>
    </div>
  </div>
  <div class="wz-next-box">
    <span class="wz-next-ic"><Sparkles :size="22" :stroke-width="1.8" aria-hidden="true" /></span>
    <div class="dd-grow">
      <p>
        <b>{{ $t('portal.wizard.done.nextTitle') }}</b>
      </p>
      <p>{{ $t('portal.wizard.done.nextText') }}</p>
    </div>
  </div>
</template>

<script setup>
import { computed, inject } from 'vue'
import { useI18n } from 'vue-i18n'
import { Sparkles } from 'lucide-vue-next'
import { AVAILABLE_LOCALES } from '@/i18n'
import { ONBOARDING_WIZARD_KEY } from '@/composables/portal/useOnboardingWizard'
import { AVATAR_CHOICE, NOTIFY_STATE, WIZARD_STEP as S } from '@/constants/portalOnboarding'
import { GENRE_PICKER, isGenrePicked } from '@/constants/portalGenres'

const V = 'portal.wizard.done.values'

const { t } = useI18n()
const wz = inject(ONBOARDING_WIZARD_KEY)

function languageValue() {
  const code = wz.choices.language
  if (code) return AVAILABLE_LOCALES.find(locale => locale.code === code)?.label || code
  return wz.instanceLanguage
    ? t(`${V}.languageDefault`, { lang: t(`portal.wizard.language.plain.${wz.instanceLanguage}`) })
    : t('portal.settings.preferences.languageDefault')
}

function notifyValue() {
  const state = wz.notify.state
  if (state === NOTIFY_STATE.GRANTED) return t(`${V}.notifyOn`)
  if (state === NOTIFY_STATE.INSECURE || state === NOTIFY_STATE.UNSUPPORTED) {
    return t(`${V}.notifyUnavailable`)
  }
  return t(`${V}.notifyOff`)
}

function avatarValue() {
  if (wz.choices.avatar === AVATAR_CHOICE.OWN && wz.choices.avatarFile) return t(`${V}.avatarOwn`)
  return t(wz.me.avatar_is_custom ? `${V}.avatarCustom` : `${V}.avatarEmby`)
}

// Features, help and expiry only show things: nothing to check or change in the recap.
const rows = computed(() => {
  const genres = GENRE_PICKER.filter(genre => isGenrePicked(genre, wz.choices.genres)).length
  return [
    { step: S.NAME, value: wz.name.shown, editable: !wz.name.locked },
    { step: S.LANGUAGE, value: languageValue(), editable: true },
    {
      step: S.VISIBILITY,
      value: t(`${V}.${wz.choices.isPublic ? 'public' : 'private'}`),
      editable: true,
    },
    { step: S.NOTIFICATIONS, value: notifyValue(), editable: true },
    { step: S.GENRES, value: t(`${V}.genres`, { n: genres }, genres), editable: true },
    { step: S.AVATAR, value: avatarValue(), editable: true },
  ]
})
</script>
