<template>
  <div class="sub-matrix glass-card">

    <!-- Header -->
    <div class="sub-matrix-header">
      <h3 class="sub-matrix-title">{{ matrixData.series_name }}</h3>
      <button class="sub-matrix-close" @click="$emit('close')">
        <X :size="14" />
      </button>
    </div>

    <!-- Coverage bars -->
    <div v-if="matrixData.coverage" class="sub-matrix-coverage">
      <div v-for="(pct, lang) in matrixData.coverage" :key="lang" class="sub-matrix-cov-row">
        <span class="sub-matrix-cov-lang">{{ lang.toUpperCase() }}</span>
        <div class="sub-matrix-cov-bar">
          <div class="sub-matrix-cov-fill" :style="{ width: pct + '%', background: pct === 100 ? '#4ade80' : pct > 50 ? '#fbbf24' : '#f43f5e' }" />
        </div>
        <span class="sub-matrix-cov-pct">{{ pct }}%</span>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="sub-matrix-center"><span class="mk-spin mk-spin-20" /></div>

    <!-- Grid -->
    <div v-else-if="Object.keys(matrixData.seasons || {}).length" class="sub-matrix-grid">
      <div v-for="(season, sNum) in sortedSeasons" :key="sNum" class="sub-matrix-season">
        <div class="sub-matrix-season-label">S{{ sNum }}</div>
        <div class="sub-matrix-episodes">
          <div
            v-for="(ep, eNum) in sortedEpisodes(season.episodes)"
            :key="eNum"
            class="sub-matrix-cell"
            :title="ep.name || `E${eNum}`"
            @click="$emit('select-episode', ep.item_id)"
          >
            <span class="sub-matrix-ep-num">{{ eNum }}</span>
            <div class="sub-matrix-dots">
              <span
                v-for="lang in matrixData.languages" :key="lang"
                class="sub-matrix-dot"
                :class="ep.status[lang] ? 'dot-ok' : 'dot-miss'"
              />
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Legend -->
    <div class="sub-matrix-legend">
      <span v-for="lang in (matrixData.languages || [])" :key="lang" class="sub-matrix-legend-item">
        <span class="sub-matrix-legend-dot" /> {{ lang.toUpperCase() }}
      </span>
      <span class="sub-matrix-legend-item"><span class="sub-matrix-legend-dot dot-ok" /> {{ $t('subtitles.filterComplete') }}</span>
      <span class="sub-matrix-legend-item"><span class="sub-matrix-legend-dot dot-miss" /> {{ $t('subtitles.filterMissing') }}</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { X } from 'lucide-vue-next'

const props = defineProps({
  matrixData: { type: Object, required: true },
  loading: { type: Boolean, default: false },
})
defineEmits(['close', 'select-episode'])

const sortedSeasons = computed(() => {
  const seasons = props.matrixData.seasons || {}
  const sorted = {}
  Object.keys(seasons).sort((a, b) => Number(a) - Number(b)).forEach(k => {
    sorted[k] = seasons[k]
  })
  return sorted
})

function sortedEpisodes(episodes) {
  if (!episodes) return {}
  const sorted = {}
  Object.keys(episodes).sort((a, b) => Number(a) - Number(b)).forEach(k => {
    sorted[k] = episodes[k]
  })
  return sorted
}
</script>

<style scoped>
.sub-matrix { padding: 16px; margin-bottom: 12px; }
.sub-matrix-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.sub-matrix-title { font-size: var(--text-base); font-weight: var(--font-medium); color: var(--text-primary); margin: 0; }
.sub-matrix-close {
  width: 28px; height: 28px; border-radius: var(--radius-btn); display: flex; align-items: center; justify-content: center;
  background: var(--surface-2); color: var(--text-muted); border: .5px solid var(--border-strong); cursor: pointer;
}
.sub-matrix-close:hover { background: rgba(244,63,94,.1); color: #fb7185; }

/* Coverage */
.sub-matrix-coverage { display: flex; gap: 12px; margin-bottom: 14px; flex-wrap: wrap; }
.sub-matrix-cov-row { display: flex; align-items: center; gap: 6px; flex: 1; min-width: 120px; }
.sub-matrix-cov-lang { font-size: var(--text-3xs); font-weight: var(--font-bold); color: var(--text-muted); min-width: 24px; }
.sub-matrix-cov-bar { flex: 1; height: 4px; border-radius: 2px; background: var(--surface-3); overflow: hidden; }
.sub-matrix-cov-fill { height: 100%; border-radius: 2px; transition: width .4s; }
.sub-matrix-cov-pct { font-size: .58rem; color: var(--text-muted); min-width: 32px; text-align: right; }

/* Center */
.sub-matrix-center { display: flex; justify-content: center; padding: 30px; }

/* Grid */
.sub-matrix-grid { display: flex; flex-direction: column; gap: 8px; }
.sub-matrix-season { display: flex; align-items: flex-start; gap: 8px; }
.sub-matrix-season-label { font-size: var(--text-2xs); font-weight: var(--font-bold); color: var(--accent-400); min-width: 28px; padding-top: 4px; }
.sub-matrix-episodes { display: flex; flex-wrap: wrap; gap: 3px; }
.sub-matrix-cell {
  width: 32px; min-height: 32px; border-radius: 4px; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 2px;
  background: rgba(255,255,255,.02); border: .5px solid var(--border-subtle); cursor: pointer; transition: all var(--duration-fast);
}
.sub-matrix-cell:hover { background: rgba(var(--accent-rgb),.08); border-color: rgba(var(--accent-rgb),.2); }
.sub-matrix-ep-num { font-size: .52rem; color: var(--text-muted); font-weight: var(--font-medium); }
.sub-matrix-dots { display: flex; gap: 2px; }
.sub-matrix-dot { width: 6px; height: 6px; border-radius: 50%; background: rgba(255,255,255,.08); }
.dot-ok { background: var(--color-success); }
.dot-miss { background: #f43f5e; }

/* Legend */
.sub-matrix-legend { display: flex; gap: 12px; margin-top: 12px; padding-top: 10px; border-top: .5px solid var(--border-subtle); }
.sub-matrix-legend-item { display: flex; align-items: center; gap: 4px; font-size: .58rem; color: var(--text-muted); }
.sub-matrix-legend-dot { width: 6px; height: 6px; border-radius: 50%; background: rgba(255,255,255,.08); }

.glass-card { background: var(--surface-1); backdrop-filter: blur(16px); border: .5px solid var(--border-default); border-radius: var(--radius-card); }
</style>
