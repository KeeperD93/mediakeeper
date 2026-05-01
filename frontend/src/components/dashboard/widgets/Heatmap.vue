<template>
  <div class="hm">
    <span class="hm-title">{{ $t('dashboard.activityWeeks') }}</span>
    <div class="hm-wrap">
      <div class="hm-grid">
        <div
          v-for="(day, i) in heatmapDays" :key="i"
          class="hm-cell"
          :style="{ background: heatColor(day.count) }"
          @mouseenter="e => showTip(e, day)"
          @mouseleave="hideTip"
        />
      </div>
      <div class="hm-legend">
        <span class="hm-legend-text">{{ $t('dashboard.less') }}</span>
        <div v-for="n in 5" :key="n" class="hm-cell hm-legend-cell" :style="{ background: heatColor(n - 1) }" />
        <span class="hm-legend-text">{{ $t('dashboard.more') }}</span>
      </div>
    </div>
    <Teleport to="body">
      <div v-if="tip.visible" class="hm-tip" :style="{ top: tip.y + 'px', left: tip.x + 'px' }">
        <div class="hm-tip-date">{{ tip.label }}</div>
        <div class="hm-tip-count">{{ $t('dashboard.plays_n', tip.count, { n: tip.count }) }}</div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useApi } from '@/composables/useApi'

const { apiGet } = useApi()
const heatmapDays = ref([])
const tip = ref({ visible: false, x: 0, y: 0, label: '', count: 0 })

function showTip(e, day) {
  const rect = e.target.getBoundingClientRect()
  tip.value = { visible: true, x: rect.left + rect.width / 2, y: rect.top - 6, label: day.label, count: day.count }
}
function hideTip() { tip.value.visible = false }

function heatColor(count) {
  if (count <= 0) return 'var(--heat-0, rgba(255,255,255,0.04))'
  if (count <= 1) return 'var(--heat-1, rgba(99,102,241,0.2))'
  if (count <= 3) return 'var(--heat-2, rgba(99,102,241,0.4))'
  if (count <= 6) return 'var(--heat-3, rgba(99,102,241,0.6))'
  return 'var(--heat-4, rgba(99,102,241,0.85))'
}

onMounted(async () => {
  const days = []
  const now = new Date()
  for (let i = 83; i >= 0; i--) {
    const d = new Date(now)
    d.setDate(d.getDate() - i)
    days.push({
      date: d.toISOString().slice(0, 10),
      count: 0,
      label: d.toLocaleDateString(undefined, { day: 'numeric', month: 'short' }),
    })
  }

  try {
    // Format: { days: [...], groups: [...], data: { "2026-03-19": { "Films": { plays: 5 }, ... } } }
    const resp = await apiGet('/api/stats/chart/daily?days=90')
    if (resp?.data && typeof resp.data === 'object') {
      const byDate = {}
      for (const [date, libraries] of Object.entries(resp.data)) {
        let total = 0
        if (typeof libraries === 'object' && libraries !== null) {
          for (const lib of Object.values(libraries)) {
            total += lib?.plays || lib?.count || (typeof lib === 'number' ? lib : 0)
          }
        }
        if (total > 0) byDate[date] = total
      }
      for (const day of days) {
        if (byDate[day.date]) day.count = byDate[day.date]
      }
    }
  } catch (e) {
    console.warn('[Heatmap.load] failed to fetch heatmap data', e)
  }

  heatmapDays.value = days
})
</script>

<style scoped>
.hm {
  background: var(--card-bg, rgba(255,255,255,0.03)); border-radius:var(--radius-card); padding: 14px;
  border: 0.5px solid var(--card-border, rgba(255,255,255,0.05));
  height: 100%; display: flex; flex-direction: column; overflow: hidden;
}
.hm-title {
  display: block; font-size: var(--text-2xs); color: var(--text-muted);
  text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; flex-shrink: 0;
}
.hm-wrap { display: flex; flex-direction: column; gap: 6px; flex: 1; min-height: 0; }
.hm-grid {
  display: grid;
  grid-template-rows: repeat(7, 1fr);
  grid-template-columns: repeat(12, 1fr);
  grid-auto-flow: column;
  gap: 2px; flex: 1; min-height: 0;
}
.hm-cell { border-radius: 2px; min-width: 0; min-height: 0; cursor: default; }
.hm-legend { display: flex; align-items: center; gap: 3px; justify-content: flex-end; flex-shrink: 0; }
.hm-legend-text { font-size: 9px; color: var(--text-muted); margin: 0 2px; }
.hm-legend-cell { width: 10px; height: 10px; min-width: 10px; border-radius: 2px; }
.hm-tip {
  position: fixed; z-index: 9999; pointer-events: none;
  transform: translate(-50%, -100%) translateY(-6px);
  background: rgba(10,14,26,0.96); border: 1px solid rgba(99,102,241,0.35);
  border-radius:var(--radius-sm); padding: 5px 10px; white-space: nowrap;
  box-shadow: 0 4px 16px rgba(0,0,0,0.4);
}
.hm-tip-date { font-size: var(--text-2xs); color: rgba(255,255,255,0.5); margin-bottom: 2px; }
.hm-tip-count { font-size: var(--text-2xs); font-weight: var(--font-medium); color: rgba(99,102,241,1); }
</style>
