<template>
  <footer class="wz-foot">
    <button v-if="wz.canBack" type="button" class="wz-ghost" @click="wz.back()">
      <ChevronLeft :size="16" aria-hidden="true" />
      {{ $t('portal.wizard.actions.back') }}
    </button>
    <p v-if="wz.footHint" class="wz-foot-hint">{{ wz.footHint }}</p>
    <button type="button" class="dd-cta wz-next" :disabled="!wz.canNext" @click="wz.next()">
      {{ wz.nextLabel }}
      <ArrowRight :size="16" :stroke-width="2.2" aria-hidden="true" />
    </button>
  </footer>
</template>

<script setup>
import { inject } from 'vue'
import { ArrowRight, ChevronLeft } from 'lucide-vue-next'
import { ONBOARDING_WIZARD_KEY } from '@/composables/portal/useOnboardingWizard'

const wz = inject(ONBOARDING_WIZARD_KEY)
</script>
