<template>
  <div class="tab-panel tab-charts-dark">
    <div class="chart-toolbar">
      <div class="chart-toggles">
        <div class="toggle-group">
          <button
            class="toggle-btn"
            :class="{ active: chartGroupBy === 'library' }"
            @click="((chartGroupBy = 'library'), reloadChart())"
          >
            {{ $t('stats.byLibrary') }}
          </button>
          <button
            class="toggle-btn"
            :class="{ active: chartGroupBy === 'user' }"
            @click="((chartGroupBy = 'user'), reloadChart())"
          >
            {{ $t('stats.byUser') }}
          </button>
        </div>
        <div class="toggle-group">
          <button
            class="toggle-btn"
            :class="{ active: chartMetric === 'count' }"
            @click="((chartMetric = 'count'), renderLine())"
          >
            {{ $t('stats.playsMetric') }}
          </button>
          <button
            class="toggle-btn"
            :class="{ active: chartMetric === 'duration' }"
            @click="((chartMetric = 'duration'), renderLine())"
          >
            {{ $t('stats.durationMetric') }}
          </button>
        </div>
      </div>
      <div class="period-pills">
        <button
          v-for="d in chartPeriodOptions"
          :key="d"
          class="pill"
          :class="{ active: chartDays === d }"
          @click="((chartDays = d), reloadChart())"
        >
          {{ d }}{{ $t('stats.daysShort') }}
        </button>
        <input
          v-model.number="chartCustomDays"
          type="number"
          min="1"
          max="9999"
          class="pill pill-input"
          :class="{ active: !chartPeriodOptions.includes(chartDays) }"
          :placeholder="$t('stats.customDays')"
          @keydown.enter="applyCustomDays"
          @blur="applyCustomDays"
        />
      </div>
    </div>
    <ChartsLineCanvas
      ref="lineCanvasRef"
      :daily-chart="dailyChart"
      :chart-group-by="chartGroupBy"
      :chart-metric="chartMetric"
      :chart-days="chartDays"
    />
    <ChartsHeatmap :daily-chart="dailyChart" :loading-chart="loadingChart" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useStats } from '@/composables/useStats'
import ChartsLineCanvas from './StatsChartsTab/ChartsLineCanvas.vue'
import ChartsHeatmap from './StatsChartsTab/ChartsHeatmap.vue'

const { dailyChart, loadingChart, loadDailyChart } = useStats()

const lineCanvasRef = ref(null)
const chartGroupBy = ref('library')
const chartMetric = ref('count')
const chartDays = ref(30)
const chartCustomDays = ref(null)
const chartPeriodOptions = [7, 30, 90, 180, 365]

function applyCustomDays() {
  const v = parseInt(chartCustomDays.value)
  if (v && v >= 1 && v <= 9999) {
    chartDays.value = v
    reloadChart()
  }
}

async function reloadChart() {
  await loadDailyChart(chartDays.value, chartGroupBy.value)
  await renderLine()
}

async function renderLine() {
  await lineCanvasRef.value?.renderChart()
}

onMounted(async () => {
  if (!dailyChart.value) {
    await reloadChart()
  } else {
    await renderLine()
  }
})
</script>

<style scoped>
.tab-charts-dark {
  background: rgb(0, 0, 0, 0.15);
  border-radius: var(--radius-card);
  padding: 12px;
  margin: -4px;
}
.chart-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  flex-wrap: wrap;
  gap: 8px;
}
.chart-toggles {
  display: flex;
  flex-flow: column wrap;
  align-items: center;
  gap: 8px;
  width: 100%;
}
.toggle-group {
  display: flex;
  gap: 6px;
  min-width: 0;
  width: 100%;
  flex-wrap: nowrap;
}
.toggle-btn {
  min-height: 32px;
  padding: 5px 12px;
  border-radius: var(--radius-pill);
  background: var(--surface-1);
  border: 1px solid var(--border-strong);
  color: rgb(255, 255, 255, 0.6);
  font-size: var(--text-2xs);
  font-weight: var(--font-extrabold);
  letter-spacing: var(--tracking-wide);
  cursor: pointer;
  transition: all 0.18s;
  backdrop-filter: var(--blur-xs);
  -webkit-tap-highlight-color: transparent;
  white-space: nowrap;
}
@media (hover: hover) {
  .toggle-btn:hover:not(.active) {
    border-color: rgb(255, 255, 255, 0.18);
    color: rgb(255, 255, 255, 0.85);
    transform: translateY(-1px);
  }
}
.toggle-btn.active {
  background: var(--gradient-pill-active);
  border-color: var(--accent-500);
  color: var(--text-primary);
  box-shadow: var(--mk-pill-shadow);
}

/* Mobile-first: the two toggle groups stack so each pair (library/user,
   plays/duration) spans the row and its two buttons split the width. */
.toggle-group .toggle-btn {
  flex: 1 1 0;
  padding: 6px 8px;
  min-width: 0;
}
@media (min-width: 768px) {
  .tab-charts-dark {
    padding: 16px;
    margin: -8px;
    margin-top: 0;
  }
  .chart-toolbar {
    gap: 12px;
    margin-bottom: 16px;
  }
  .chart-toggles {
    flex-direction: row;
    gap: 6px;
    width: auto;
  }
  .toggle-group {
    width: auto;
    flex-wrap: wrap;
  }
  .toggle-group .toggle-btn {
    flex: initial;
    padding: 5px 12px;
    min-width: auto;
  }
}
</style>
