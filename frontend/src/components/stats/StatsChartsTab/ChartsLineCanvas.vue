<template>
  <div class="glass-card chart-card">
    <div class="chart-sub">
      {{ chartMetric === 'count' ? $t('stats.playsMetric') : $t('stats.durationMetric') }}
      {{ chartGroupBy === 'library' ? $t('stats.byLibrary') : $t('stats.byUser') }} —
      {{ chartDays }}{{ $t('stats.daysShort') }}
    </div>
    <div class="chart-container"><canvas ref="chartCanvas" /></div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'

const props = defineProps({
  dailyChart: { type: Object, default: null },
  chartGroupBy: { type: String, required: true },
  chartMetric: { type: String, required: true },
  chartDays: { type: Number, required: true },
})

const { t } = useI18n()

const chartCanvas = ref(null)
let chartInstance = null
let ChartCtor = null

const CC = [
  '#f59e0b',
  '#ef4444',
  '#22c55e',
  '#3b82f6',
  '#a855f7',
  '#06b6d4',
  '#ec4899',
  '#84cc16',
  '#f97316',
  '#6366f1',
  '#14b8a6',
  '#e11d48',
]

async function ensureChartJs() {
  if (ChartCtor) return ChartCtor
  const module = await import('chart.js/auto')
  ChartCtor = module.Chart || module.default
  return ChartCtor
}

async function renderChart() {
  if (!props.dailyChart || !chartCanvas.value) return
  let Chart
  try {
    Chart = await ensureChartJs()
  } catch {
    return
  }
  if (chartInstance) chartInstance.destroy()
  const d = props.dailyChart
  const lb = d.days.map(x => {
    const p = x.split('-')
    return `${p[2]}/${p[1]}`
  })
  const ds = d.groups.map((g, i) => {
    const c = CC[i % CC.length]
    return {
      label: g,
      data: d.days.map(day => {
        const gd = (d.data[day] || {})[g] || {}
        return props.chartMetric === 'count'
          ? gd.count || 0
          : Math.round((gd.duration || 0) / 1e7 / 60)
      }),
      borderColor: c,
      backgroundColor: c + '33',
      fill: true,
      tension: 0.3,
      pointRadius: 0,
      pointHitRadius: 8,
      borderWidth: 2,
    }
  })
  const rs = getComputedStyle(document.body)
  const tc = rs.getPropertyValue('--text-secondary').trim() || '#9ca3af'
  const mc = rs.getPropertyValue('--text-muted').trim() || '#4b5563'
  chartInstance = new Chart(chartCanvas.value.getContext('2d'), {
    type: 'line',
    data: { labels: lb, datasets: ds },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: {
          position: 'bottom',
          labels: {
            color: tc,
            usePointStyle: true,
            pointStyle: 'circle',
            padding: 15,
            font: { size: 11 },
          },
        },
        tooltip: {
          backgroundColor: 'rgba(17,24,39,0.95)',
          titleColor: '#fff',
          bodyColor: '#d1d5db',
          borderColor: '#374151',
          borderWidth: 1,
          cornerRadius: 8,
          padding: 10,
        },
      },
      scales: {
        x: {
          grid: { color: 'rgba(75,85,99,0.15)' },
          ticks: { color: mc, font: { size: 10 }, maxTicksLimit: 20, maxRotation: 45 },
        },
        y: {
          beginAtZero: true,
          grid: { color: 'rgba(75,85,99,0.15)' },
          ticks: { color: mc, font: { size: 10 } },
          title: {
            display: true,
            text:
              props.chartMetric === 'count' ? t('stats.playsMetric') : t('stats.minutesLabel'),
            color: mc,
          },
        },
      },
    },
  })
}

defineExpose({ renderChart })

watch(() => props.dailyChart, renderChart)
watch(() => props.chartMetric, renderChart)

onMounted(() => {
  if (props.dailyChart) renderChart()
})

onUnmounted(() => {
  if (chartInstance) {
    chartInstance.destroy()
    chartInstance = null
  }
})
</script>

<style scoped>
.chart-sub {
  font-size: var(--text-xs);
  color: var(--text-muted);
  margin-bottom: 14px;
}
.chart-container {
  position: relative;
  height: 380px;
}
.glass-card {
  background: var(--surface-1);
  backdrop-filter: blur(16px);
  border: 0.5px solid var(--border-default);
  border-radius: var(--radius-card);
}
.chart-card {
  padding: 20px;
}

@media (max-width: 767px) {
  .chart-container {
    height: 280px;
  }
}
</style>
