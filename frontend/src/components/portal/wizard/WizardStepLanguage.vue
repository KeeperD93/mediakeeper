<template>
  <div class="wz-opts" role="radiogroup" :aria-labelledby="headingId">
    <WizardOption
      :name="groupName"
      :label="$t('portal.settings.preferences.languageDefault')"
      :hint="defaultHint"
      :checked="wz.choices.language === null"
      @pick="wz.choices.language = null"
    />
    <WizardOption
      v-for="locale in AVAILABLE_LOCALES"
      :key="locale.code"
      :name="groupName"
      :label="locale.label"
      :hint="$t('portal.wizard.language.ownHint', {}, { locale: locale.code })"
      :hint-lang="locale.code"
      :checked="wz.choices.language === locale.code"
      @pick="wz.choices.language = locale.code"
    />
  </div>
  <WizardWhere path="preferences" :lead="$t('portal.wizard.language.switchNote')" />
</template>

<script setup>
import { computed, inject, useId } from 'vue'
import { useI18n } from 'vue-i18n'
import { AVAILABLE_LOCALES } from '@/i18n'
import {
  ONBOARDING_HEADING_KEY,
  ONBOARDING_WIZARD_KEY,
} from '@/composables/portal/useOnboardingWizard'
import WizardOption from './WizardOption.vue'
import WizardWhere from './WizardWhere.vue'

const { t } = useI18n()
const wz = inject(ONBOARDING_WIZARD_KEY)
const headingId = inject(ONBOARDING_HEADING_KEY)
const groupName = useId()

// « Default » says which language that is today, when the server told us.
const defaultHint = computed(() =>
  wz.instanceLanguage
    ? t('portal.wizard.language.defaultHint', {
        lang: t(`portal.wizard.language.now.${wz.instanceLanguage}`),
      })
    : t('portal.wizard.language.defaultHintUnknown'),
)
</script>
