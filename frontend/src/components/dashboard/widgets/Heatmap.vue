<template>
  <div class="hm">
    <span class="hm-title">{{ $t('dashboard.activityWeeks') }}</span>
    <div class="hm-wrap">
      <div class="hm-grid">
        <div
          v-for="(day, i) in heatmapDays"
          :key="i"
          class="hm-cell"
          :style="{ background: heatColor(day.count) }"
          @mouseenter="e => showTip(e, day)"
          @mouseleave="hideTip"
        />
      </div>
      <div class="hm-legend">
        <span class="hm-legend-text">{{ $t('dashboard.less') }}</span>
        <div
          v-for="step in LEGEND_STEPS"
          :key="step"
          class="hm-cell hm-legend-cell"
          :style="{ background: `var(--heat-${step})` }"
        />
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
import { localizedDate } from '@/utils/datetime'

const { apiGet } = useApi()
const heatmapDays = ref([])
const tip = ref({ visible: false, x: 0, y: 0, label: '', count: 0 })

// One swatch per intensity bucket — decoupled from heatColor() so the
// legend always shows the full gradient even after the play-count
// breakpoints are re-tuned.
const LEGEND_STEPS = [0, 1, 2, 3, 4]

function showTip(e, day) {
  const rect = e.target.getBoundingClientRect()
  tip.value = {
    visible: true,
    x: rect.left + rect.width / 2,
    y: rect.top - 6,
    label: day.label,
    count: day.count,
  }
}
function hideTip() {
  tip.value.visible = false
}

function heatColor(count) {
  // The --heat-N scale is declared in dashboard-view.css as
  // rgb(var(--color-success-rgb), 0.2..0.85). No fallback needed
  // since the stylesheet is loaded with the dashboard view.
  //
  // Breakpoints widened so an active server (regular daily playback)
  // still shows visible contrast across the 12-week grid instead of
  // saturating at heat-4 after just a handful of plays.
  if (count <= 0) return 'var(--heat-0)'
  if (count <= 4) return 'var(--heat-1)'
  if (count <= 12) return 'var(--heat-2)'
  if (count <= 25) return 'var(--heat-3)'
  return 'var(--heat-4)'
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
      label: localizedDate(d, { day: 'numeric', month: 'short' }),
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
  background: var(--card-bg);
  border-radius: var(--radius-card);
  padding: var(--space-3-5);
  border: var(--border-width-thin) solid var(--card-border);
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.hm-title {
  display: block;
  font-size: var(--text-2xs);
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: var(--tracking-widest);
  margin-bottom: var(--space-2);
  flex-shrink: 0;
}
.hm-wrap {
  display: flex;
  flex-direction: column;
  /* 6 px between grid and legend — between --space-1 (4) and
     --space-2 (8). */
  gap: 6px;
  flex: 1;
  min-height: 0;
}
.hm-grid {
  display: grid;
  grid-template-rows: repeat(7, 1fr);
  grid-template-columns: repeat(12, 1fr);
  grid-auto-flow: column;
  gap: var(--space-half);
  flex: 1;
  min-height: 0;
}
.hm-cell {
  /* 2 px cell radius — below --radius-sm. Widget-local for the
     fine-grained heatmap squares. */
  border-radius: 2px;
  min-width: 0;
  min-height: 0;
  cursor: default;
}
.hm-legend {
  display: flex;
  align-items: center;
  /* 3 px legend gap — tighter than --space-1 to keep the legend
     compact under the grid. */
  gap: 3px;
  justify-content: flex-end;
  flex-shrink: 0;
}
.hm-legend-text {
  /* 9 px micro-label below --text-3xs (~9.9). Widget-local. */
  font-size: 9px;
  color: var(--text-muted);
  margin: 0 var(--space-half);
}
.hm-legend-cell {
  /* 10 px legend swatch — too small for --icon-* (12+) but bigger
     than a grid cell to read as a sample. */
  width: 10px;
  height: 10px;
  min-width: 10px;
  border-radius: 2px;
}
.hm-tip {
  position: fixed;
  z-index: var(--z-toast);
  pointer-events: none;
  /* 6 px lift above the cursor — between --space-1 (4) and
     --space-2 (8). */
  transform: translate(-50%, -100%) translateY(-6px);
  background: var(--bg-primary);
  border: var(--border-width) solid rgb(var(--color-success-rgb), 0.35);
  border-radius: var(--radius-sm);
  /* 5 / 10 px tooltip padding — vertical between --space-1 and
     --space-2, horizontal --space-2-5. */
  padding: 5px var(--space-2-5);
  white-space: nowrap;
  box-shadow: var(--shadow-sm);
}
.hm-tip-date {
  font-size: var(--text-2xs);
  color: var(--text-faint);
  margin-bottom: var(--space-half);
}
.hm-tip-count {
  font-size: var(--text-2xs);
  font-weight: var(--font-medium);
  color: var(--color-success);
}
</style>
