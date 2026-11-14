<template>
  <div v-if="!wz.full" class="wz-note">
    <Info :size="18" aria-hidden="true" />
    <p>{{ $t('portal.wizard.name.resetInfo') }}</p>
  </div>
  <!-- A locked name cannot be changed: the warning about choosing it has no object. -->
  <div v-if="!name.locked" class="wz-note wz-note--warn" role="note">
    <TriangleAlert :size="18" aria-hidden="true" />
    <p>{{ $t('portal.wizard.name.warning') }}</p>
  </div>

  <div class="wz-field">
    <label class="wz-label" :for="inputId">{{ $t('portal.wizard.name.label') }}</label>
    <div class="wz-inputwrap">
      <input
        v-if="name.locked"
        :id="inputId"
        class="wz-input"
        type="text"
        :value="name.value"
        readonly
        :aria-describedby="`${rulesId} ${messageId}`"
      />
      <input
        v-else
        :id="inputId"
        class="wz-input"
        :class="{ 'is-ok': name.free, 'is-err': name.invalid }"
        type="text"
        :value="name.value"
        maxlength="50"
        autocomplete="off"
        spellcheck="false"
        :placeholder="placeholder"
        :aria-invalid="name.invalid ? 'true' : 'false'"
        :aria-describedby="`${rulesId} ${messageId}`"
        @input="name.input($event.target.value)"
      />
      <Lock v-if="name.locked" class="wz-lockic" :size="18" aria-hidden="true" />
    </div>
    <p :id="rulesId" class="wz-rules">{{ $t('portal.wizard.name.rules') }}</p>
    <p :id="messageId" class="wz-msg" :class="`wz-msg--${name.message.tone}`" aria-live="polite">
      {{ name.message.text }}
      <button v-if="name.failed" type="button" class="wz-link" @click="name.retry()">
        {{ $t('portal.wizard.name.retry') }}
      </button>
    </p>
    <div v-if="name.suggestions.length" class="wz-sugg">
      <span>{{ $t('portal.wizard.name.suggestions') }}</span>
      <div class="wz-chips">
        <button
          v-for="suggestion in name.suggestions"
          :key="suggestion"
          type="button"
          class="wz-chip"
          @click="name.input(suggestion)"
        >
          {{ suggestion }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, inject, useId } from 'vue'
import { useI18n } from 'vue-i18n'
import { Info, Lock, TriangleAlert } from 'lucide-vue-next'
import { ONBOARDING_WIZARD_KEY } from '@/composables/portal/useOnboardingWizard'
import { WIZARD_ACCOUNT } from '@/constants/portalOnboarding'

const { t } = useI18n()
const wz = inject(ONBOARDING_WIZARD_KEY)
// The name's refs read unwrapped through the shared reactive store.
const name = wz.name
const inputId = useId()
const rulesId = useId()
const messageId = useId()

const placeholder = computed(() => {
  if (!wz.full) return t('portal.wizard.name.placeholderReset')
  return wz.account === WIZARD_ACCOUNT.NEW ? t('portal.wizard.name.placeholderNew') : ''
})
</script>
