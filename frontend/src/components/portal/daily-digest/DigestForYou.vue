<template>
  <section :aria-label="$t('portal.dailyDigest.sections.forYou')">
    <div class="dd-sh">
      <h2 class="dd-st">{{ $t('portal.dailyDigest.sections.forYou') }}</h2>
    </div>
    <div class="dd-box">
      <div v-for="row in rows" :key="row.key" class="dd-fy-row">
        <span class="dd-fy-ic" :class="`dd-tone--${row.tone}`">
          <component :is="row.icon" :size="18" aria-hidden="true" />
        </span>
        <div class="dd-grow">
          <span class="dd-fy-t">{{ row.text }}</span>
          <span class="dd-fy-s">{{ row.sub }}</span>
        </div>
        <router-link v-if="row.to" :to="row.to" class="dd-link" @click="$emit('leave')">
          {{ row.link }}
        </router-link>
      </div>
    </div>
  </section>
</template>

<script setup>
import '@/assets/styles/portal/daily-digest-lists.css'

defineProps({
  // « For you » rows written by useDailyDigestPresenters (`forYou`).
  rows: { type: Array, required: true },
})
defineEmits(['leave'])
</script>
