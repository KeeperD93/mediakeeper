<template>
  <div v-if="compact" class="ddc-expiry" role="status">
    <span class="ddc-dot dd-tone--warn">
      <Clock :size="14" :stroke-width="2.2" aria-hidden="true" />
    </span>
    <span class="dd-grow">
      <b>{{ expiry.lead }}</b>
      {{ expiry.whenShort }} {{ expiry.hintShort }}
    </span>
  </div>
  <div v-else class="dd-expiry" role="status">
    <span class="dd-expiry-ic"><Clock :size="18" aria-hidden="true" /></span>
    <div class="dd-grow">
      <p class="dd-expiry-t">{{ expiry.title }}</p>
      <p class="dd-expiry-s">{{ expiry.hint }}</p>
    </div>
  </div>
</template>

<script setup>
import { Clock } from 'lucide-vue-next'

defineProps({
  // Texts written by useDailyDigestPresenters (`expiry`).
  expiry: { type: Object, required: true },
  compact: { type: Boolean, default: false },
})
</script>
