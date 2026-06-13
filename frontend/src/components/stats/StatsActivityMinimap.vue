<template>
  <div class="minimap-wrap glass-card">
    <div class="minimap-header">
      <span class="minimap-title">{{ $t('stats.last24h') }}</span>
      <span class="minimap-count">{{ minimapStats.total }} {{ $t('stats.plays_unit') }}</span>
    </div>
    <div class="minimap-hours">
      <div
        v-for="h in 24"
        :key="'mh24' + h"
        class="minimap-hour-col"
        :title="minimapHourData[h - 1].title"
      >
        <div
          class="minimap-hour-fill"
          :class="'minimap-hour-fill--' + minimapHourData[h - 1].state"
          :style="{ height: minimapHourData[h - 1].pct + '%' }"
        />
      </div>
    </div>
    <div class="minimap-hlabels">
      <span v-for="h in [0, 3, 6, 9, 12, 15, 18, 21]" :key="'ml' + h" class="minimap-hlabel">
        {{ h }}h
      </span>
    </div>
    <div class="minimap-legend">
      <span class="minimap-leg">
        <span class="minimap-ldot minimap-ldot-direct" />
        {{ $t('stats.directPlay') }}
      </span>
      <span class="minimap-leg">
        <span class="minimap-ldot minimap-ldot-transcode" />
        {{ $t('stats.transcodeLabel') }}
      </span>
      <span class="minimap-leg">
        <span class="minimap-ldot minimap-ldot-other" />
        {{ $t('stats.otherStream') }}
      </span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

const props = defineProps({
  items: { type: Array, default: () => [] },
})

const { t } = useI18n()

const minimapStats = computed(() => ({ total: props.items.length }))
const minimapHourData = computed(() => {
  const hours = Array.from({ length: 24 }, () => ({ direct: 0, transcode: 0, other: 0, users: [] }))
  for (const i of props.items) {
    const h = new Date(i.started_at).getHours()
    if (i.play_method === 'DirectPlay') hours[h].direct++
    else if (i.play_method === 'Transcode') hours[h].transcode++
    else hours[h].other++
    if (!hours[h].users.includes(i.user)) hours[h].users.push(i.user)
  }
  const maxCount = Math.max(1, ...hours.map(h => h.direct + h.transcode + h.other))
  return hours.map((h, idx) => {
    const total = h.direct + h.transcode + h.other
    // transcode-dominant hours read warning, any other play reads success,
    // empty hours stay transparent — the colour itself lives on the token class.
    const state = h.transcode > h.direct ? 'transcode' : total > 0 ? 'active' : 'empty'
    const users = h.users.length ? t('stats.minimapHourUsers', { users: h.users.join(', ') }) : ''
    return {
      pct: Math.round((total / maxCount) * 100),
      state,
      title: t('stats.minimapHourTooltip', { hour: idx, count: total }) + users,
    }
  })
})
</script>

<style scoped>
.minimap-wrap {
  padding: 14px 16px;
  margin-bottom: 0;
}
.minimap-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 10px;
}
.minimap-title {
  font-size: var(--text-2xs);
  font-weight: var(--font-medium);
  color: var(--text-primary);
}
.minimap-count {
  font-size: var(--text-2xs);
  color: var(--text-muted);
}
.minimap-hours {
  display: flex;
  align-items: flex-end;
  gap: 3px;
  height: 48px;
  padding: 0 2px;
}
.minimap-hour-col {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: flex-end;
  height: 100%;
  background: rgb(255, 255, 255, 0.02);
  border-radius: 3px 3px 0 0;
  cursor: default;
  transition: background var(--duration-fast);
}
.minimap-hour-col:hover {
  background: var(--surface-3);
}
.minimap-hour-fill {
  width: 100%;
  border-radius: 3px 3px 0 0;
  min-height: 0;
  transition: height var(--duration-slow) ease;
}
.minimap-hour-fill--transcode {
  background: var(--color-warning);
}
.minimap-hour-fill--active {
  background: var(--color-success);
}
.minimap-hour-fill--empty {
  background: transparent;
}
.minimap-hlabels {
  display: flex;
  justify-content: space-between;
  padding: 4px 2px 0;
}
.minimap-hlabel {
  font-size: 0.5rem;
  color: var(--text-muted);
  width: calc(100% / 8);
  text-align: center;
}
.minimap-legend {
  display: flex;
  gap: 12px;
  margin-top: 8px;
  justify-content: center;
}
.minimap-leg {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 0.58rem;
  color: var(--text-muted);
}
.minimap-ldot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}
.minimap-ldot-direct {
  background: var(--color-success);
}
.minimap-ldot-transcode {
  background: var(--color-warning);
}
.minimap-ldot-other {
  background: var(--accent-400);
}
.glass-card {
  background: var(--surface-1);
  backdrop-filter: blur(16px);
  border: 0.5px solid var(--border-default);
  border-radius: var(--radius-card);
}
</style>
