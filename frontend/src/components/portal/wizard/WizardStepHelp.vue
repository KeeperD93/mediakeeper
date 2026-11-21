<template>
  <div class="wzh">
    <HelpDemoPlayer :initial="initial" />
    <HelpGuides />
  </div>
</template>

<script setup>
// Body of the wizard's « Aides » step; the wizard draws its pill, title and subtitle.
import HelpDemoPlayer from './help/HelpDemoPlayer.vue'
import HelpGuides from './help/HelpGuides.vue'
import '@/assets/styles/portal/wizard-help.css'

defineProps({
  // First letter of the member's name, drawn in the reduced top bars.
  initial: { type: String, default: '' },
})
</script>
