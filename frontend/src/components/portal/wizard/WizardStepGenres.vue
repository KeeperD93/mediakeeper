<template>
  <div class="wz-chips" role="group" :aria-labelledby="headingId">
    <button
      v-for="genre in GENRE_PICKER"
      :key="genre.label"
      type="button"
      class="wz-chip"
      :class="{ 'is-on': picked(genre) }"
      :aria-pressed="picked(genre) ? 'true' : 'false'"
      @click="wz.choices.genres = toggleGenrePick(genre, wz.choices.genres)"
    >
      <!-- Each genre's colour, the same as in Settings › Preferences. -->
      <span class="wz-gdot" :style="{ '--wz-genre': genre.color }" />
      {{ $t(`portal.genres.${genre.label}`) }}
      <Check class="wz-tick" :size="14" :stroke-width="2.6" aria-hidden="true" />
    </button>
  </div>
  <WizardWhere path="preferences" :lead="lead" aria-live="polite" />
</template>

<script setup>
import { computed, inject } from 'vue'
import { useI18n } from 'vue-i18n'
import { Check } from 'lucide-vue-next'
import {
  ONBOARDING_HEADING_KEY,
  ONBOARDING_WIZARD_KEY,
} from '@/composables/portal/useOnboardingWizard'
import { GENRE_PICKER, isGenrePicked, toggleGenrePick } from '@/constants/portalGenres'
import WizardWhere from './WizardWhere.vue'

const { t } = useI18n()
const wz = inject(ONBOARDING_WIZARD_KEY)
const headingId = inject(ONBOARDING_HEADING_KEY)

const picked = genre => isGenrePicked(genre, wz.choices.genres)
const count = computed(() => GENRE_PICKER.filter(picked).length)
const lead = computed(
  () =>
    `${t('portal.wizard.genres.count', { n: count.value }, count.value)} · ${t('portal.wizard.genres.visible')}`,
)
</script>
