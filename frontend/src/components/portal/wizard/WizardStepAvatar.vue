<template>
  <div class="wz-avrow">
    <WizardAvatar size="lg" :src="wz.avatarSrc" :initial="wz.initial" :tier="wz.me.tier" />
    <p class="wz-where">{{ $t(`portal.wizard.avatar.state.${stateKey}`) }}</p>
  </div>
  <div class="wz-opts wz-opts--2" role="radiogroup" :aria-labelledby="headingId">
    <WizardOption
      :name="groupName"
      :label="$t(`portal.wizard.avatar.keep.${current}`)"
      :hint="$t(`portal.wizard.avatar.keepHint.${current}`)"
      :checked="wz.choices.avatar === AVATAR_CHOICE.KEEP"
      @pick="wz.chooseAvatar(AVATAR_CHOICE.KEEP)"
    />
    <WizardOption
      :name="groupName"
      :label="$t('portal.wizard.avatar.own')"
      :hint="$t(`portal.wizard.avatar.ownHint.${current}`)"
      :checked="wz.choices.avatar === AVATAR_CHOICE.OWN"
      @pick="wz.chooseAvatar(AVATAR_CHOICE.OWN)"
    />
  </div>
  <div v-if="wz.choices.avatar === AVATAR_CHOICE.OWN" class="wz-upload">
    <input
      ref="fileRef"
      class="wz-file"
      type="file"
      :accept="AVATAR_TYPES.join(',')"
      tabindex="-1"
      aria-hidden="true"
      @change="onFile"
    />
    <button type="button" class="wz-ghost" @click="fileRef?.click()">
      <ImagePlus :size="16" aria-hidden="true" />
      {{ $t(wz.choices.avatarFile ? 'portal.wizard.avatar.replace' : 'portal.wizard.avatar.pick') }}
    </button>
    <p v-if="wz.choices.avatarProblem" class="wz-msg wz-msg--err" role="alert">
      {{ $t(`portal.wizard.avatar.problem.${wz.choices.avatarProblem}`) }}
    </p>
  </div>
  <WizardWhere path="identity" />
</template>

<script setup>
import { computed, inject, ref, useId } from 'vue'
import { ImagePlus } from 'lucide-vue-next'
import {
  ONBOARDING_HEADING_KEY,
  ONBOARDING_WIZARD_KEY,
} from '@/composables/portal/useOnboardingWizard'
import { AVATAR_CHOICE, AVATAR_TYPES } from '@/constants/portalOnboarding'
import WizardAvatar from './WizardAvatar.vue'
import WizardOption from './WizardOption.vue'
import WizardWhere from './WizardWhere.vue'

const wz = inject(ONBOARDING_WIZARD_KEY)
const headingId = inject(ONBOARDING_HEADING_KEY)
const groupName = useId()
const fileRef = ref(null)

// The picture the account has today: Emby's, or one sent from Settings.
const current = wz.me.avatar_is_custom ? 'custom' : 'emby'
const stateKey = computed(() =>
  wz.choices.avatar === AVATAR_CHOICE.OWN && wz.choices.avatarFile ? 'picked' : current,
)

function onFile(event) {
  const [file] = event.target.files || []
  if (file) wz.pickAvatar(file)
  // The same file picked again must still fire a change.
  event.target.value = ''
}
</script>
