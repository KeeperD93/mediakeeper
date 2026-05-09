<template>
  <div>
    <div class="top-head">
      <span class="top-title">{{ $t('stats.differentFlux') }}</span>
    </div>
    <div v-if="!byMethod.length" class="top-empty">{{ $t('stats.noData') }}</div>
    <div v-else class="donut-wrap">
      <svg class="donut-svg" viewBox="0 0 120 120">
        <circle
          v-for="(seg, i) in donutSegments"
          :key="i"
          cx="60"
          cy="60"
          r="48"
          fill="none"
          stroke-width="14"
          :stroke-dasharray="seg.dash"
          :stroke-dashoffset="seg.offset"
          stroke-linecap="round"
          class="donut-seg"
          :style="{ animationDelay: i * 150 + 'ms', stroke: seg.color }"
        />
        <text x="60" y="56" text-anchor="middle" class="donut-total">{{ fluxTotal }}</text>
        <text x="60" y="70" text-anchor="middle" class="donut-sub">
          {{ $t('stats.plays_unit') }}
        </text>
      </svg>
      <div class="donut-legend">
        <div v-for="it in byMethod" :key="it.method" class="donut-leg">
          <span class="donut-dot" :style="{ background: fluxColor(it.method) }" />
          <span class="donut-name">{{ it.method }}</span>
          <span class="donut-pct">{{ fluxPct(it.count) }}%</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  byMethod: { type: Array, default: () => [] },
})

const CIRC = 2 * Math.PI * 48
function fluxColor(m) {
  return m === 'DirectPlay'
    ? 'var(--color-success)'
    : m === 'Transcode'
      ? 'var(--color-warning)'
      : 'var(--color-info)'
}
const fluxTotal = computed(() => props.byMethod.reduce((s, x) => s + x.count, 0))
function fluxPct(c) {
  const tot = fluxTotal.value
  return tot > 0 ? ((c / tot) * 100).toFixed(1) : '0'
}
const donutSegments = computed(() => {
  const tot = fluxTotal.value || 1
  const segs = []
  let off = CIRC * 0.25
  for (const x of props.byMethod) {
    const pct = x.count / tot
    const dash = pct * CIRC
    segs.push({ color: fluxColor(x.method), dash: `${dash} ${CIRC - dash}`, offset: -off })
    off += dash
  }
  return segs
})
</script>

<style scoped>
.top-head {
  display: flex;
  justify-content: space-between;
  margin-bottom: 10px;
}
.top-title {
  font-size: var(--text-2xs);
  font-weight: var(--font-medium);
  text-transform: uppercase;
  letter-spacing: 0.3px;
  color: rgb(255, 255, 255, 0.7);
}
.top-empty {
  font-size: var(--text-2xs);
  color: var(--text-muted);
  padding: 6px 0;
}
.donut-wrap {
  display: flex;
  align-items: center;
  gap: 16px;
}
.donut-svg {
  width: 100px;
  height: 100px;
  flex-shrink: 0;
}
.donut-seg {
  animation: pc-donut-in 0.6s ease-out both;
}
@keyframes pc-donut-in {
  from {
    stroke-dasharray: 0 301.6;
  }
}
.donut-total {
  font-size: var(--text-md);
  font-weight: var(--font-medium);
  fill: var(--text-primary);
}
.donut-sub {
  font-size: 9px;
  fill: rgb(255, 255, 255, 0.35);
}
.donut-legend {
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex: 1;
  min-width: 0;
}
.donut-leg {
  display: flex;
  align-items: center;
  gap: 6px;
}
.donut-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.donut-name {
  font-size: var(--text-2xs);
  color: rgb(255, 255, 255, 0.7);
  flex: 1;
}
.donut-pct {
  font-size: var(--text-2xs);
  font-weight: var(--font-medium);
  color: rgb(255, 255, 255, 0.5);
}
</style>
