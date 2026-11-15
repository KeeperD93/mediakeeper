<template>
  <div class="wz-opts wz-opts--2" role="radiogroup" :aria-labelledby="headingId">
    <WizardOption
      :name="groupName"
      :label="$t('portal.wizard.visibility.public')"
      :hint="$t('portal.wizard.visibility.publicHint')"
      :badge="$t('portal.wizard.visibility.recommended')"
      :checked="wz.choices.isPublic"
      :disabled="forced"
      @pick="wz.choices.isPublic = true"
    >
      <template #icon><Globe :size="16" aria-hidden="true" /></template>
    </WizardOption>
    <WizardOption
      :name="groupName"
      :label="$t('portal.wizard.visibility.private')"
      :hint="$t('portal.wizard.visibility.privateHint')"
      :checked="!wz.choices.isPublic"
      :disabled="forced"
      @pick="wz.choices.isPublic = false"
    >
      <template #icon><Lock :size="16" aria-hidden="true" /></template>
    </WizardOption>
  </div>
  <p v-if="forced" class="wz-where">{{ $t('portal.settings.visibility.publicLocked') }}</p>
  <div v-if="!wz.choices.isPublic" class="wz-note" role="status">
    <Info :size="18" aria-hidden="true" />
    <div>
      <p>{{ $t('portal.wizard.visibility.privateXp') }}</p>
      <p>{{ $t('portal.wizard.visibility.privateChat') }}</p>
    </div>
  </div>
  <WizardWhere when="anytime" path="visibility" />
</template>

<script setup>
import { inject, useId } from 'vue'
import { Globe, Info, Lock } from 'lucide-vue-next'
import {
  ONBOARDING_HEADING_KEY,
  ONBOARDING_WIZARD_KEY,
} from '@/composables/portal/useOnboardingWizard'
import WizardOption from './WizardOption.vue'
import WizardWhere from './WizardWhere.vue'

const wz = inject(ONBOARDING_WIZARD_KEY)
const headingId = inject(ONBOARDING_HEADING_KEY)
const groupName = useId()
// Made public by an administrator: the choice is shown, greyed.
const forced = !!wz.me.forced_public
</script>
