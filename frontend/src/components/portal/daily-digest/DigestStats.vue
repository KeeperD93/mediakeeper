<template>
  <section :aria-label="$t('portal.dailyDigest.aria.stats')">
    <div v-if="compact" class="ddc-stats">
      <div v-for="card in cards" :key="card.key" class="ddc-stat">
        <component
          :is="card.icon"
          class="ddc-stat-icon"
          :class="`dd-stat-icon--${card.key}`"
          :size="18"
          aria-hidden="true"
        />
        <b class="ddc-stat-value">
          {{ card.compactValue ?? card.value }}
          <em
            v-if="card.delta"
            class="ddc-stat-delta"
            :class="{ 'dd-delta--down': card.deltaDown }"
          >
            {{ card.delta }}
          </em>
        </b>
        <span class="ddc-stat-caption">{{ card.compactCaption }}</span>
      </div>
    </div>
    <div v-else class="dd-stats">
      <div v-for="card in cards" :key="card.key" class="dd-stat">
        <component
          :is="card.icon"
          class="dd-stat-icon"
          :class="`dd-stat-icon--${card.key}`"
          :size="22"
          aria-hidden="true"
        />
        <span class="dd-stat-label">{{ card.label }}</span>
        <div class="dd-stat-value">
          {{ card.value }}
          <span
            v-if="card.delta"
            class="dd-stat-delta"
            :class="{ 'dd-delta--down': card.deltaDown }"
          >
            {{ card.delta }}
          </span>
        </div>
        <span class="dd-stat-caption">{{ card.caption }}</span>
      </div>
    </div>
  </section>
</template>

<script setup>
defineProps({
  // Figures of the day written by useDailyDigestPresenters (`statCards`).
  cards: { type: Array, required: true },
  compact: { type: Boolean, default: false },
})
</script>
