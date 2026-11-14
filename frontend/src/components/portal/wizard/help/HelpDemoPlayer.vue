<template>
  <div class="wzh-demo" :class="{ 'is-paused': paused, 'is-still': still }">
    <div class="wzh-demo-head">
      <div class="wzh-chips" role="group" :aria-label="$t('portal.wizardHelp.demosLabel')">
        <button
          v-for="id in DEMO_ORDER"
          :key="id"
          type="button"
          class="wzh-chip"
          :class="{ 'is-on': demo === id }"
          :aria-pressed="demo === id ? 'true' : 'false'"
          @click="pick(id)"
        >
          {{ $t(`portal.wizardHelp.demos.${id}`) }}
        </button>
      </div>
      <div v-if="still" class="wzh-stepper">
        <button
          type="button"
          class="wzh-ctrl wzh-ctrl--icon"
          :aria-label="$t('portal.wizardHelp.prevView')"
          @click="step(-1)"
        >
          <ChevronLeft :size="16" aria-hidden="true" />
        </button>
        <span class="wzh-stepper-count" aria-live="polite">
          {{ $t('portal.wizardHelp.viewCount', { n: frame + 1, total: views }) }}
        </span>
        <button
          type="button"
          class="wzh-ctrl wzh-ctrl--icon"
          :aria-label="$t('portal.wizardHelp.nextView')"
          @click="step(1)"
        >
          <ChevronRight :size="16" aria-hidden="true" />
        </button>
      </div>
      <button v-else type="button" class="wzh-ctrl" @click="togglePause">
        <Play v-if="paused" :size="16" aria-hidden="true" />
        <Pause v-else :size="16" aria-hidden="true" />
        {{ $t(paused ? 'portal.wizardHelp.play' : 'portal.wizardHelp.pause') }}
      </button>
    </div>

    <div ref="boxRef" class="wzh-stage-box">
      <!-- Decorative: the numbered captions below say the same thing in words. -->
      <div class="wzh-stage" :style="stageStyle" aria-hidden="true">
        <div class="wzh-canvas">
          <component :is="SCREENS[demo]" :key="demo" :frame="frame" :initial="initial" />
        </div>
      </div>
    </div>

    <ol class="wzh-caps" :aria-label="$t(`portal.wizardHelp.captionsLabel.${demo}`)">
      <li
        v-for="n in views"
        :key="`${demo}-${n}`"
        class="wzh-cap"
        :class="{ 'is-on': frame === n - 1 }"
        :aria-current="frame === n - 1 ? 'step' : undefined"
      >
        <span class="wzh-cap-n" aria-hidden="true">{{ n }}</span>
        <span>{{ $t(`portal.wizardHelp.captions.${demo}.s${n}`) }}</span>
      </li>
    </ol>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { ChevronLeft, ChevronRight, Pause, Play } from 'lucide-vue-next'
import DemoListFrames from './DemoListFrames.vue'
import DemoRequestFrames from './DemoRequestFrames.vue'
import DemoTicketFrames from './DemoTicketFrames.vue'
import { DEMO, DEMO_ORDER } from '@/constants/portalWizardHelp'
import { useDemoPlayer } from '@/composables/portal/useDemoPlayer'
import { useStageScale } from '@/composables/portal/useStageScale'
import '@/assets/styles/portal/wizard-help.css'
import '@/assets/styles/portal/wizard-help-motion.css'
import '@/assets/styles/portal/wizard-help-screens.css'
import '@/assets/styles/portal/wizard-help-pages.css'
import '@/assets/styles/portal/wizard-help-sheets.css'
import '@/assets/styles/portal/wizard-help-dialogs.css'

defineProps({
  initial: { type: String, default: '' },
})

const SCREENS = {
  [DEMO.REQUEST]: DemoRequestFrames,
  [DEMO.TICKET]: DemoTicketFrames,
  [DEMO.LIST]: DemoListFrames,
}

const { demo, frame, paused, still, views, frameMs, pick, togglePause, step } = useDemoPlayer()
const boxRef = ref(null)
const scale = useStageScale(boxRef)

// Both values come from the code at run time: the measured scale and the demo's pace.
const stageStyle = computed(() => ({
  '--wzh-scale': scale.value,
  '--wzh-frame-dur': `${frameMs.value}ms`,
}))
</script>
