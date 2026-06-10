<template>
  <div v-if="pct !== null" class="act-prog">
    <div
      class="act-prog-track"
      role="progressbar"
      :aria-valuenow="pct"
      aria-valuemin="0"
      aria-valuemax="100"
      :aria-label="$t('stats.watchedPercent', { pct })"
    >
      <div class="act-prog-fill" :style="{ width: pct + '%' }" />
      <span class="act-prog-pct">{{ pct }}%</span>
    </div>
    <span class="act-prog-time">
      {{ positionLabel }}
      <span class="act-prog-sep">/</span>
      {{ runtimeLabel }}
    </span>
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
  align-items: center;
  gap: 8px;
}
.act-prog-track {
  position: relative;
  flex: 1;
  min-width: 0;
  height: 20px;
  background: var(--surface-3);
  border-radius: var(--radius-sm);
  overflow: hidden;
}
.act-prog-fill {
  position: absolute;
  inset: 0 auto 0 0;
  height: 100%;
  background: linear-gradient(90deg, rgb(var(--color-success-rgb), 0.85), var(--color-success));
  transition: width var(--duration-slow) ease;
}
.act-prog-pct {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--text-2xs);
  font-weight: var(--font-medium);
  color: var(--text-primary);
  text-shadow: var(--text-shadow-subtle);
  font-variant-numeric: tabular-nums;
}
.act-prog-time {
  flex: none;
  width: 110px;
  font-size: var(--text-2xs);
  color: var(--text-muted);
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
}
.act-prog-sep {
  opacity: 0.5;
}
.act-prog-na {
  color: var(--text-muted);
}
</style>
