<template>
  <Teleport to="body">
    <!-- No way out but the last button: no cross, no Escape, no click beside. -->
    <div class="dd-overlay wz-overlay">
      <div
        ref="panelRef"
        class="dd-panel wz"
        :class="{ 'wz--still': still }"
        role="dialog"
        aria-modal="true"
        :aria-labelledby="titleId"
        tabindex="-1"
      >
        <span :id="titleId" class="sr-only">{{ $t(dialogLabelKey) }}</span>
        <!-- The step scrolls; the footer under it never moves. -->
        <div ref="bodyRef" class="wz-in">
          <WizardProgress v-if="wz.progress" :num="wz.progress.num" :total="wz.progress.total" />

          <section
            :key="wz.step"
            class="wz-step"
            :class="`wz-step--${wz.step}`"
            :aria-labelledby="headingId"
          >
            <img
              v-if="banner"
              class="wz-banner"
              :class="{ 'wz-banner--sm': !wz.full }"
              :src="BRAND_BANNER_SRC"
              :alt="$t('portal.wizard.bannerAlt')"
            />
            <header class="wz-head">
              <WizardAvatar
                v-if="wz.step === WIZARD_STEP.DONE"
                class="wz-head-av"
                size="hero"
                :src="wz.avatarSrc"
                :initial="wz.initial"
                :tier="wz.me.tier"
              />
              <div class="dd-grow">
                <span v-if="wz.head.eyebrow" class="dd-date">{{ wz.head.eyebrow }}</span>
                <h1 :id="headingId" ref="headingRef" class="dd-hello wz-hello" tabindex="-1">
                  {{ wz.head.title }}
                </h1>
                <p class="dd-sub">{{ wz.head.sub }}</p>
              </div>
            </header>
            <WizardStepHelp v-if="wz.step === WIZARD_STEP.HELP" :initial="wz.initial" />
            <component :is="BODIES[wz.step]" v-else />
          </section>

          <p v-if="wz.saveFailed" class="wz-error" role="alert">
            {{ $t('portal.wizard.saveFailed') }}
          </p>
        </div>
        <WizardFoot />
      </div>
    </div>
  </Teleport>
</template>

<script setup>
// The digest's sheets first: the wizard wears the same window, hello and buttons.
import '@/assets/styles/portal/daily-digest-shell.css'
import '@/assets/styles/portal/daily-digest-common.css'
import '@/assets/styles/portal/daily-digest-full.css'
import '@/assets/styles/portal/wizard.css'
import '@/assets/styles/portal/wizard-window.css'
import '@/assets/styles/portal/wizard-fields.css'
import '@/assets/styles/portal/wizard-steps.css'
import '@/assets/styles/portal/wizard-navmap.css'
import '@/assets/styles/portal/wizard-profile.css'
import { computed, nextTick, provide, ref, useId, watch } from 'vue'
import { useBodyScrollLock } from '@/composables/useBodyScrollLock'
import { useFocusTrap } from '@/composables/useFocusTrap'
import { usePrefersReducedMotion } from '@/composables/usePrefersReducedMotion'
import {
  ONBOARDING_HEADING_KEY,
  ONBOARDING_WIZARD_KEY,
  useOnboardingWizard,
} from '@/composables/portal/useOnboardingWizard'
import { BRAND_BANNER_SRC } from '@/constants/brand'
import { WIZARD_MODE, WIZARD_STEP } from '@/constants/portalOnboarding'
import WizardAvatar from './WizardAvatar.vue'
import WizardFoot from './WizardFoot.vue'
import WizardProgress from './WizardProgress.vue'
import WizardStepAvatar from './WizardStepAvatar.vue'
import WizardStepDone from './WizardStepDone.vue'
import WizardStepExpiry from './WizardStepExpiry.vue'
import WizardStepFeatures from './WizardStepFeatures.vue'
import WizardStepGenres from './WizardStepGenres.vue'
import WizardStepHelp from './WizardStepHelp.vue'
import WizardStepLanguage from './WizardStepLanguage.vue'
import WizardStepName from './WizardStepName.vue'
import WizardStepNotifications from './WizardStepNotifications.vue'
import WizardStepVisibility from './WizardStepVisibility.vue'
import WizardStepWelcome from './WizardStepWelcome.vue'

const BODIES = {
  [WIZARD_STEP.WELCOME]: WizardStepWelcome,
  [WIZARD_STEP.NAME]: WizardStepName,
  [WIZARD_STEP.LANGUAGE]: WizardStepLanguage,
  [WIZARD_STEP.VISIBILITY]: WizardStepVisibility,
  [WIZARD_STEP.FEATURES]: WizardStepFeatures,
  [WIZARD_STEP.EXPIRY]: WizardStepExpiry,
  [WIZARD_STEP.NOTIFICATIONS]: WizardStepNotifications,
  [WIZARD_STEP.GENRES]: WizardStepGenres,
  [WIZARD_STEP.AVATAR]: WizardStepAvatar,
  [WIZARD_STEP.DONE]: WizardStepDone,
}

const props = defineProps({
  mode: {
    type: String,
    required: true,
    validator: value => Object.values(WIZARD_MODE).includes(value),
  },
})
const emit = defineEmits(['done'])

const wz = useOnboardingWizard(props.mode, () => emit('done'))
provide(ONBOARDING_WIZARD_KEY, wz)

const titleId = useId()
const headingId = useId()
provide(ONBOARDING_HEADING_KEY, headingId)
const panelRef = ref(null)
const bodyRef = ref(null)
const headingRef = ref(null)
const still = usePrefersReducedMotion()

const dialogLabelKey = computed(() =>
  wz.full ? 'portal.wizard.dialogLabel' : 'portal.wizard.dialogLabelReset',
)
// The banner opens the tour and tops the name reset; the steps between go without.
const banner = computed(() => !wz.full || wz.step === WIZARD_STEP.WELCOME)

const open = ref(true)
// « What's new today? » takes the focus when the wizard hands over: none to give back.
useFocusTrap({
  active: open,
  containerRef: panelRef,
  initialFocusRef: headingRef,
  returnFocusOnDeactivate: false,
})
useBodyScrollLock(open)

// Each step opens at its top and is announced by its title: the focus lands on it.
watch(
  () => wz.step,
  () =>
    nextTick(() => {
      bodyRef.value.scrollTop = 0
      headingRef.value?.focus()
    }),
)
</script>
