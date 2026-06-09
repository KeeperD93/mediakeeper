<template>
  <div v-if="pct !== null" class="act-prog">
    <span class="act-prog-label">
      {{ positionLabel }}
      <span class="act-prog-sep">/</span>
      {{ runtimeLabel }}
    </span>
    <div
      class="act-prog-track"
      role="progressbar"
      :aria-valuenow="pct"
      aria-valuemin="0"
      aria-valuemax="100"
      :aria-label="$t('stats.watchedPercent', { pct })"
    >
      <div class="act-prog-fill" :style="{ width: pct + '%' }" />
    </div>
  </div>
  <span v-else class="act-prog-na">—</span>
</template>

<script setup>
import { computed } from 'vue'
import { useStats } from '@/composables/useStats'
import { watchedPct } from '@/components/stats/statsTableUtils'

const props = defineProps({
  position: { type: Number, default: 0 },
  runtime: { type: Number, default: 0 },
})

const { ticksToDuration } = useStats()
const pct = computed(() => watchedPct(props.position, props.runtime))
const positionLabel = computed(() => ticksToDuration(props.position))
const runtimeLabel = computed(() => ticksToDuration(props.runtime))
</script>

<style scoped>
.act-prog {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 96px;
}
.act-prog-label {
  font-size: var(--text-2xs);
  color: var(--text-muted);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}
.act-prog-sep {
  opacity: 0.5;
}
.act-prog-track {
  height: 6px;
  background: var(--surface-3);
  border-radius: var(--radius-pill);
  overflow: hidden;
}
.act-prog-fill {
  height: 100%;
  border-radius: var(--radius-pill);
  background: linear-gradient(90deg, rgb(var(--color-success-rgb), 0.8), var(--color-success));
  transition: width var(--duration-slow) ease;
}
.act-prog-na {
  color: var(--text-muted);
}
</style>
