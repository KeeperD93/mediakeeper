<template>
  <div class="tab-panel tab-charts-dark">
    <div class="chart-toolbar">
      <div class="chart-toggles">
        <div class="toggle-group"><button class="toggle-btn" :class="{ active: chartGroupBy === 'library' }" @click="chartGroupBy = 'library'; reloadChart()">{{ $t('stats.byLibrary') }}</button><button class="toggle-btn" :class="{ active: chartGroupBy === 'user' }" @click="chartGroupBy = 'user'; reloadChart()">{{ $t('stats.byUser') }}</button></div>
        <div class="toggle-group"><button class="toggle-btn" :class="{ active: chartMetric === 'count' }" @click="chartMetric = 'count'; renderChart()">{{ $t('stats.playsMetric') }}</button><button class="toggle-btn" :class="{ active: chartMetric === 'duration' }" @click="chartMetric = 'duration'; renderChart()">{{ $t('stats.durationMetric') }}</button></div>
      </div>
      <div class="period-pills">
        <button v-for="d in chartPeriodOptions" :key="d" class="pill" :class="{ active: chartDays === d }" @click="chartDays = d; reloadChart()">{{ d }}{{ $t('stats.daysShort') }}</button>
        <input v-model.number="chartCustomDays" type="number" min="1" max="9999" class="pill pill-input"
          :class="{ active: !chartPeriodOptions.includes(chartDays) }"
          :placeholder="$t('stats.customDays')" @keydown.enter="applyCustomDays" @blur="applyCustomDays" />
      </div>
    </div>
    <div class="glass-card chart-card">
      <div class="chart-sub">{{ chartMetric === 'count' ? $t('stats.playsMetric') : $t('stats.durationMetric') }} {{ chartGroupBy === 'library' ? $t('stats.byLibrary') : $t('stats.byUser') }} — {{ chartDays }}{{ $t('stats.daysShort') }}</div>
      <div class="chart-container"><canvas ref="chartCanvas" /></div>
    </div>
    <div class="glass-card chart-card chart-card-spaced">
      <div class="chart-card-title">{{ $t('stats.annualActivity') }}</div>
      <div v-if="loadingChart" class="chart-skel-wrap"><div class="skel-line w70" /><div class="skel-line w50 skel-line-mt8" /></div>
      <div v-else-if="hmMonthGrid.length" class="hm-stats-wrap">
        <div class="hm-month-header">
          <div class="hm-month-row-label" />
          <div v-for="d in 31" :key="d" class="hm-month-day-num">{{ d }}</div>
        </div>
        <div class="hm-month-body">
          <div v-for="(row, ri) in hmMonthGrid" :key="ri" class="hm-month-row">
            <div class="hm-month-row-label">{{ row.label }}</div>
            <div v-for="(cell, di) in row.days" :key="di"
              class="hm-stats-cell"
              :style="{ background: cell.date ? hmCellColor(cell.count) : 'transparent', visibility: cell.date ? 'visible' : 'hidden' }"
              @mouseenter="e => hmTooltipShow(e, cell)"
              @mouseleave="hmTooltipHide" />
          </div>
        </div>
        <div class="hm-stats-footer">
          <div class="hm-wc-peak">
            <Zap :size="10" />
            {{ $t('stats.peakMonth', { label: hmMonthPeak.label, count: hmMonthPeak.count }) }}
          </div>
          <div class="hm-stats-legend">
            <span class="hm-stats-leg-txt">{{ $t('stats.less') }}</span>
            <div v-for="n in 5" :key="n" class="hm-stats-leg-cell" :style="{ background: hmCellColor((n - 1) * 3) }" />
            <span class="hm-stats-leg-txt">{{ $t('stats.more') }}</span>
          </div>
        </div>
      </div>
      <Teleport to="body">
        <div v-if="hmTip.visible" class="hm-stats-tooltip" :style="{ top: hmTip.y + 'px', left: hmTip.x + 'px' }">
          <div class="hm-tip-date">{{ hmTip.label }}</div>
          <div class="hm-tip-count">{{ $t('dashboard.plays_n', hmTip.count, { n: hmTip.count }) }}</div>
        </div>
      </Teleport>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useStats } from '@/composables/useStats'
import { Zap } from 'lucide-vue-next'

const { t, locale } = useI18n()
const { dailyChart, loadingChart, loadDailyChart } = useStats()

function localeTag() {
  const l = locale.value || 'fr'
  return l === 'fr' ? 'fr-FR' : l === 'en' ? 'en-US' : l
}

const chartCanvas = ref(null)
const chartGroupBy = ref('library')
const chartMetric = ref('count')
const chartDays = ref(30)
const chartCustomDays = ref(null)
const chartPeriodOptions = [7, 30, 90, 180, 365]
let chartInstance = null
let ChartCtor = null

const CC = ['#f59e0b', '#ef4444', '#22c55e', '#3b82f6', '#a855f7', '#06b6d4', '#ec4899', '#84cc16', '#f97316', '#6366f1', '#14b8a6', '#e11d48']

function applyCustomDays() {
  const v = parseInt(chartCustomDays.value)
  if (v && v >= 1 && v <= 9999) { chartDays.value = v; reloadChart() }
}

async function ensureChartJs() {
  if (ChartCtor) return ChartCtor
  const module = await import('chart.js/auto')
  ChartCtor = module.Chart || module.default
  return ChartCtor
}

async function reloadChart() {
  await loadDailyChart(chartDays.value, chartGroupBy.value)
  await renderChart()
}

async function renderChart() {
  if (!dailyChart.value || !chartCanvas.value) return
  let Chart = null
  try { Chart = await ensureChartJs() } catch { return }
  if (chartInstance) chartInstance.destroy()
  const d = dailyChart.value
  const lb = d.days.map(x => { const p = x.split('-'); return `${p[2]}/${p[1]}` })
  const ds = d.groups.map((g, i) => {
    const c = CC[i % CC.length]
    return {
      label: g,
      data: d.days.map(day => {
        const gd = (d.data[day] || {})[g] || {}
        return chartMetric.value === 'count' ? (gd.count || 0) : Math.round((gd.duration || 0) / 1e7 / 60)
      }),
      borderColor: c, backgroundColor: c + '33',
      fill: true, tension: .3, pointRadius: 0, pointHitRadius: 8, borderWidth: 2,
    }
  })
  const rs = getComputedStyle(document.body)
  const tc = rs.getPropertyValue('--text-secondary').trim() || '#9ca3af'
  const mc = rs.getPropertyValue('--text-muted').trim() || '#4b5563'
  chartInstance = new Chart(chartCanvas.value.getContext('2d'), {
    type: 'line',
    data: { labels: lb, datasets: ds },
    options: {
      responsive: true, maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { position: 'bottom', labels: { color: tc, usePointStyle: true, pointStyle: 'circle', padding: 15, font: { size: 11 } } },
        tooltip: { backgroundColor: 'rgba(17,24,39,0.95)', titleColor: '#fff', bodyColor: '#d1d5db', borderColor: '#374151', borderWidth: 1, cornerRadius: 8, padding: 10 },
      },
      scales: {
        x: { grid: { color: 'rgba(75,85,99,0.15)' }, ticks: { color: mc, font: { size: 10 }, maxTicksLimit: 20, maxRotation: 45 } },
        y: { beginAtZero: true, grid: { color: 'rgba(75,85,99,0.15)' }, ticks: { color: mc, font: { size: 10 } }, title: { display: true, text: chartMetric.value === 'count' ? t('stats.playsMetric') : t('stats.minutesLabel'), color: mc } },
      },
    },
  })
}

const hmMonthGrid = computed(() => {
  if (!dailyChart.value?.data) return []
  const byDate = {}
  for (const [date, libs] of Object.entries(dailyChart.value.data)) {
    let total = 0
    if (typeof libs === 'object' && libs !== null)
      for (const lib of Object.values(libs)) total += lib?.plays || lib?.count || (typeof lib === 'number' ? lib : 0)
    if (total > 0) byDate[date] = total
  }
  const now = new Date()
  now.setHours(0, 0, 0, 0)
  const rows = []
  for (let m = 11; m >= 0; m--) {
    const refDate = new Date(now.getFullYear(), now.getMonth() - m, 1)
    const year = refDate.getFullYear()
    const month = refDate.getMonth()
    const daysInMonth = new Date(year, month + 1, 0).getDate()
    const lt = localeTag()
    const label = refDate.toLocaleDateString(lt, { month: 'short', year: '2-digit' })
    const days = []
    for (let d = 1; d <= 31; d++) {
      if (d > daysInMonth) { days.push({ count: 0, label: '', date: '' }); continue }
      const dayDate = new Date(year, month, d)
      if (dayDate > now) { days.push({ count: 0, label: '', date: '' }); continue }
      const iso = `${year}-${String(month + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`
      const lbl = dayDate.toLocaleDateString(lt, { day: 'numeric', month: 'long', year: 'numeric' })
      days.push({ count: byDate[iso] || 0, label: lbl, date: iso })
    }
    rows.push({ label, days })
  }
  return rows
})

const hmGridMax = computed(() => {
  if (!hmMonthGrid.value.length) return 1
  return Math.max(1, ...hmMonthGrid.value.flatMap(r => r.days.map(d => d.count)))
})

function hmCellColor(count) {
  if (!count) return 'var(--heat-0, rgba(255,255,255,0.05))'
  const r = count / hmGridMax.value
  if (r <= 0.15) return 'var(--heat-1, rgba(99,102,241,0.2))'
  if (r <= 0.35) return 'var(--heat-2, rgba(99,102,241,0.4))'
  if (r <= 0.65) return 'var(--heat-3, rgba(99,102,241,0.65))'
  return 'var(--heat-4, rgba(99,102,241,0.9))'
}

const hmMonthPeak = computed(() => {
  let mx = 0, lbl = '—'
  for (const row of hmMonthGrid.value)
    for (const d of row.days)
      if (d.count > mx) { mx = d.count; lbl = d.label }
  return { count: mx, label: lbl }
})

const hmTip = ref({ visible: false, x: 0, y: 0, label: '', count: 0 })
function hmTooltipShow(e, cell) {
  if (!cell.date) return
  const rect = e.target.getBoundingClientRect()
  hmTip.value = { visible: true, x: rect.left + rect.width / 2, y: rect.top - 8, label: cell.label, count: cell.count }
}
function hmTooltipHide() { hmTip.value.visible = false }

onMounted(async () => {
  if (!dailyChart.value) {
    await reloadChart()
  } else {
    await renderChart()
  }
})

onUnmounted(() => {
  if (chartInstance) { chartInstance.destroy(); chartInstance = null }
})
</script>

<style scoped>
.tab-charts-dark { background: rgba(0,0,0,.15); border-radius: var(--radius-card); padding: 16px; margin: -8px; margin-top: 0; }
.chart-toolbar { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; flex-wrap: wrap; gap: 12px; }
.chart-toggles { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.toggle-group { display: flex; gap: 6px; min-width: 0; flex-wrap: wrap; }
.toggle-btn {
  min-height: 32px;
  padding: 5px 12px;
  border-radius: var(--radius-pill);
  background: rgba(255,255,255,0.03);
  border: 1px solid var(--border-strong);
  color: rgba(255,255,255,.6);
  font-size: var(--text-2xs);
  font-weight: var(--font-extrabold);
  letter-spacing: var(--tracking-wide);
  cursor: pointer;
  transition: all .18s;
  backdrop-filter: var(--blur-xs);
  -webkit-tap-highlight-color: transparent;
  white-space: nowrap;
}
@media (hover: hover) {
  .toggle-btn:hover:not(.active) {
    border-color: rgba(255,255,255,0.18);
    color: rgba(255,255,255,.85);
    transform: translateY(-1px);
  }
}
.toggle-btn.active {
  background: var(--gradient-pill-active);
  border-color: var(--accent-500);
  color: #fff;
  box-shadow: var(--mk-pill-shadow);
}
.chart-sub { font-size: var(--text-xs); color: var(--text-muted); margin-bottom: 14px; }
.chart-container { position: relative; height: 380px; }
.chart-card-title { font-size: var(--text-base); font-weight: var(--font-medium); color: var(--text-primary); margin-bottom: 14px; }
.glass-card { background: var(--surface-1); backdrop-filter: blur(16px); border: .5px solid var(--border-default); border-radius: var(--radius-card); }

.hm-stats-wrap { display: flex; flex-direction: column; gap: 0; width: 100%; }
.hm-month-header, .hm-month-row { display: grid; grid-template-columns: 52px repeat(31, 1fr); gap: 2px; width: 100%; align-items: center; }
.hm-month-header { margin-bottom: 4px; }
.hm-month-row-label { font-size: var(--text-3xs); color: var(--text-muted); text-align: right; padding-right: 8px; white-space: nowrap; }
.hm-month-day-num { text-align: center; font-size: .55rem; color: var(--text-muted); opacity: .5; user-select: none; }
.hm-month-body { display: flex; flex-direction: column; gap: 3px; width: 100%; }
.hm-stats-cell { height: 20px; width: 100%; border-radius: 3px; transition: filter .08s; cursor: default; min-width: 0; }
.hm-stats-cell:hover { filter: brightness(1.45); cursor: pointer; }
.hm-stats-footer { display: flex; align-items: center; justify-content: space-between; margin-top: 12px; padding-top: 8px; border-top: .5px solid var(--border-default); }
.hm-stats-legend { display: flex; align-items: center; gap: 4px; }
.hm-stats-leg-txt { font-size: var(--text-3xs); color: var(--text-muted); margin: 0 2px; }
.hm-stats-leg-cell { width: 18px; height: 18px; border-radius: 3px; flex-shrink: 0; }
.hm-wc-peak { display: flex; align-items: center; gap: 6px; font-size: var(--text-2xs); color: var(--text-muted); }
.hm-wc-peak svg { color: var(--accent-400); }
.hm-stats-tooltip { position: fixed; z-index: 9999; background: rgba(10,14,26,.96); border: 1px solid rgba(99,102,241,.35); border-radius: var(--radius-sm); padding: 6px 10px; pointer-events: none; transform: translate(-50%, -100%) translateY(-6px); white-space: nowrap; box-shadow: 0 4px 16px rgba(0,0,0,.4); }
.hm-tip-date { font-size: var(--text-2xs); color: rgba(255,255,255,.5); margin-bottom: 2px; text-transform: capitalize; }
.hm-tip-count { font-size: var(--text-2xs); font-weight: var(--font-medium); color: rgba(var(--accent-rgb), 1); }
.skel-line { height: 12px; border-radius: 4px; background: linear-gradient(90deg, rgba(255,255,255,.02) 25%, rgba(255,255,255,.05) 50%, rgba(255,255,255,.02) 75%); background-size: 200% 100%; animation: ch-sk var(--duration-animation) ease-in-out infinite; }
.w50 { width: 50%; } .w70 { width: 70%; }
@keyframes ch-sk { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }
.chart-card { padding: 20px; }
.chart-card-spaced { margin-top: 14px; }
.chart-skel-wrap { padding: 20px 0; }
.skel-line-mt8 { margin-top: 8px; }

/* Mobile — keep the toggle rows compact so nothing overflows the card */
@media (max-width: 767px) {
  .tab-charts-dark { padding: 12px; margin: -4px; }
  .chart-toolbar { gap: 8px; margin-bottom: 12px; }
  .toggle-group { gap: 6px; }
  .toggle-btn { padding: 5px 10px; font-size: var(--text-2xs); min-width: 0; }
  .chart-container { height: 280px; }
}
</style>
