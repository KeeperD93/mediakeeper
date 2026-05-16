<template>
  <div class="glass-card chart-card chart-card-spaced">
    <div class="chart-card-title">{{ $t('stats.annualActivity') }}</div>
    <div v-if="loadingChart" class="chart-skel-wrap">
      <div class="skel-line w70" />
      <div class="skel-line w50 skel-line-mt8" />
    </div>
    <div v-else-if="hmMonthGrid.length" class="hm-stats-wrap">
      <div class="hm-month-header">
        <div class="hm-month-row-label" />
        <div v-for="d in 31" :key="d" class="hm-month-day-num">{{ d }}</div>
      </div>
      <div class="hm-month-body">
        <div v-for="(row, ri) in hmMonthGrid" :key="ri" class="hm-month-row">
          <div class="hm-month-row-label">{{ row.label }}</div>
          <div
            v-for="(cell, di) in row.days"
            :key="di"
            class="hm-stats-cell"
            :style="{
              background: cell.date ? hmCellColor(cell.count) : 'transparent',
              visibility: cell.date ? 'visible' : 'hidden',
            }"
            @mouseenter="e => hmTooltipShow(e, cell)"
            @mouseleave="hmTooltipHide"
          />
        </div>
      </div>
      <div class="hm-stats-footer">
        <div class="hm-wc-peak">
          <Zap :size="10" />
          {{ $t('stats.peakMonth', { label: hmMonthPeak.label, count: hmMonthPeak.count }) }}
        </div>
        <div class="hm-stats-legend">
          <span class="hm-stats-leg-txt">{{ $t('stats.less') }}</span>
          <div
            v-for="n in 5"
            :key="n"
            class="hm-stats-leg-cell"
            :style="{ background: hmCellColor((n - 1) * 3) }"
          />
          <span class="hm-stats-leg-txt">{{ $t('stats.more') }}</span>
        </div>
      </div>
    </div>
    <Teleport to="body">
      <div
        v-if="hmTip.visible"
        class="hm-stats-tooltip"
        :style="{ top: hmTip.y + 'px', left: hmTip.x + 'px' }"
      >
        <div class="hm-tip-date">{{ hmTip.label }}</div>
        <div class="hm-tip-count">
          {{ $t('dashboard.plays_n', hmTip.count, { n: hmTip.count }) }}
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { toRef } from 'vue'
import { useI18n } from 'vue-i18n'
import { Zap } from 'lucide-vue-next'
import { useChartsHeatmap } from './useChartsHeatmap'

const props = defineProps({
  dailyChart: { type: Object, default: null },
  loadingChart: { type: Boolean, default: false },
})

const { locale } = useI18n()

const { hmMonthGrid, hmCellColor, hmMonthPeak, hmTip, hmTooltipShow, hmTooltipHide } =
  useChartsHeatmap(toRef(props, 'dailyChart'), locale)
</script>

<style scoped>
.chart-card-title {
  font-size: var(--text-base);
  font-weight: var(--font-medium);
  color: var(--text-primary);
  margin-bottom: 14px;
}
.glass-card {
  background: var(--surface-1);
  backdrop-filter: blur(16px);
  border: 0.5px solid var(--border-default);
  border-radius: var(--radius-card);
}

.hm-stats-wrap {
  display: flex;
  flex-direction: column;
  gap: 0;
  width: 100%;
}
.hm-month-header,
.hm-month-row {
  display: grid;
  grid-template-columns: 52px repeat(31, 1fr);
  gap: 2px;
  width: 100%;
  align-items: center;
}
.hm-month-header {
  margin-bottom: 4px;
}
.hm-month-row-label {
  font-size: var(--text-3xs);
  color: var(--text-muted);
  text-align: right;
  padding-right: 8px;
  white-space: nowrap;
}
.hm-month-day-num {
  text-align: center;
  font-size: 0.55rem;
  color: var(--text-muted);
  opacity: 0.5;
  user-select: none;
}
.hm-month-body {
  display: flex;
  flex-direction: column;
  gap: 3px;
  width: 100%;
}
.hm-stats-cell {
  height: 20px;
  width: 100%;
  border-radius: 3px;
  transition: filter 0.08s;
  cursor: default;
  min-width: 0;
}
.hm-stats-cell:hover {
  filter: brightness(1.45);
  cursor: pointer;
}
.hm-stats-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 12px;
  padding-top: 8px;
  border-top: 0.5px solid var(--border-default);
}
.hm-stats-legend {
  display: flex;
  align-items: center;
  gap: 4px;
}
.hm-stats-leg-txt {
  font-size: var(--text-3xs);
  color: var(--text-muted);
  margin: 0 2px;
}
.hm-stats-leg-cell {
  width: 18px;
  height: 18px;
  border-radius: 3px;
  flex-shrink: 0;
}
.hm-wc-peak {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: var(--text-2xs);
  color: var(--text-muted);
}
.hm-wc-peak svg {
  color: var(--accent-400);
}
.hm-stats-tooltip {
  position: fixed;
  z-index: 9999;
  background: rgb(10, 14, 26, 0.96);
  border: 1px solid rgb(99, 102, 241, 0.35);
  border-radius: var(--radius-sm);
  padding: 6px 10px;
  pointer-events: none;
  transform: translate(-50%, -100%) translateY(-6px);
  white-space: nowrap;
  box-shadow: 0 4px 16px rgb(0, 0, 0, 0.4);
}
.hm-tip-date {
  font-size: var(--text-2xs);
  color: rgb(255, 255, 255, 0.5);
  margin-bottom: 2px;
  text-transform: capitalize;
}
.hm-tip-count {
  font-size: var(--text-2xs);
  font-weight: var(--font-medium);
  color: rgb(var(--accent-rgb), 1);
}
.skel-line {
  height: 12px;
  border-radius: 4px;
  background: linear-gradient(
    90deg,
    rgb(255, 255, 255, 0.02) 25%,
    rgb(255, 255, 255, 0.05) 50%,
    rgb(255, 255, 255, 0.02) 75%
  );
  background-size: 200% 100%;
  animation: ch-sk var(--duration-animation) ease-in-out infinite;
}
.w50 {
  width: 50%;
}
.w70 {
  width: 70%;
}
@keyframes ch-sk {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}
.chart-card {
  padding: 20px;
}
.chart-card-spaced {
  margin-top: 14px;
}
.chart-skel-wrap {
  padding: 20px 0;
}
.skel-line-mt8 {
  margin-top: 8px;
}

@media (max-width: 767px) {
  /* Narrow screens can't fit 31 day numbers without overflow. Keep only
     a handful of markers (1, 7, 14, 21, 28) so the timeline still gives
     a visual anchor while the empty slots reserve the grid layout. */
  .hm-month-header,
  .hm-month-row {
    grid-template-columns: 32px repeat(31, 1fr);
    gap: 1px;
  }
  .hm-month-row-label {
    font-size: 0.55rem;
    padding-right: 4px;
  }
  .hm-month-day-num {
    visibility: hidden;
    font-size: 0.45rem;
  }
  .hm-month-header > :nth-child(2),
  .hm-month-header > :nth-child(8),
  .hm-month-header > :nth-child(15),
  .hm-month-header > :nth-child(22),
  .hm-month-header > :nth-child(29) {
    visibility: visible;
  }
  .chart-card {
    padding: 14px 12px;
  }
}
</style>
