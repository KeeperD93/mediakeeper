<template>
  <div v-if="pct !== null" class="act-seg">
    <div
      class="act-seg-track"
      role="img"
      :aria-label="$t('stats.segmentBarLabel', { count: sessions.length, pct })"
    >
      <div
        v-for="(s, i) in segments"
        :key="i"
        class="act-seg-fill"
        :class="{ 'act-seg-latest': s.latest }"
        :style="{ left: s.left + '%', width: s.width + '%' }"
      />
      <span class="act-seg-pct">{{ pct }}%</span>
    </div>
    <span class="act-seg-time">
      {{ positionLabel }}
      <span class="act-seg-sep">/</span>
      {{ runtimeLabel }}
    </span>
  </div>
  <span v-else class="act-seg-na">—</span>
</template>

<script setup>
import { computed } from 'vue'
import { useStats } from '@/composables/useStats'
import { watchedPct } from '@/components/stats/statsTableUtils'

const props = defineProps({
  // Furthest position reached across the group, for the % + numeric label.
  position: { type: Number, default: 0 },
  runtime: { type: Number, default: 0 },
  // Sessions of the group, newest-first (as returned by the backend).
  sessions: { type: Array, default: () => [] },
})

const { ticksToDuration } = useStats()
const pct = computed(() => watchedPct(props.position, props.runtime))
const positionLabel = computed(() => ticksToDuration(props.position))
const runtimeLabel = computed(() => ticksToDuration(props.runtime))

// One span per session, oldest-first. Forward progress extends from the previous
// position; a rewind (re-watch) starts a fresh span from 0 so the replay stays
// visible. Earlier sessions render grey, the most recent one green.
const segments = computed(() => {
  const rt = props.runtime
  if (!rt || rt <= 0) return []
  const chrono = [...props.sessions].reverse()
  let prev = 0
  const segs = []
  chrono.forEach((s, i) => {
    const pos = Math.max(0, Math.min(s.position_ticks || 0, rt))
    const latest = i === chrono.length - 1
    segs.push({ start: pos < prev ? 0 : prev, end: pos, latest })
    prev = pos
  })
  return segs
    .filter(s => s.end > s.start)
    .map(s => ({ ...s, left: (s.start / rt) * 100, width: ((s.end - s.start) / rt) * 100 }))
})
</script>

<style scoped>
.act-seg {
  display: flex;
  align-items: center;
  gap: 8px;
}
.act-seg-track {
  position: relative;
  flex: 1;
  min-width: 0;
  height: 20px;
  background: var(--surface-3);
  border-radius: var(--radius-sm);
  overflow: hidden;
}
.act-seg-fill {
  position: absolute;
  top: 0;
  height: 100%;
  background: rgb(var(--text-primary-rgb), 0.28);
  border-left: 1px solid var(--surface-1);
}
/* The most recent session is highlighted green; earlier passes stay grey. */
.act-seg-latest {
  background: var(--color-success);
}
.act-seg-pct {
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
.act-seg-time {
  flex: none;
  width: 110px;
  font-size: var(--text-2xs);
  color: var(--text-muted);
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
}
.act-seg-sep {
  opacity: 0.5;
}
.act-seg-na {
  color: var(--text-muted);
}
</style>
