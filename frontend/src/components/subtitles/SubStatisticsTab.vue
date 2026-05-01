<template>
  <div class="sub-panel">

    <!-- Loading -->
    <div v-if="loading" class="sub-center"><span class="mk-spin mk-spin-24" /></div>

    <template v-else-if="stats">

      <!-- Quick stats cards -->
      <div class="sub-stat-cards">
        <div class="sub-stat-card glass-card">
          <span class="sub-stat-value">{{ stats.total_downloads }}</span>
          <span class="sub-stat-label">{{ $t('subtitles.totalDownloads') }}</span>
        </div>
        <div class="sub-stat-card glass-card">
          <span class="sub-stat-value">{{ stats.avg_score || '—' }}</span>
          <span class="sub-stat-label">{{ $t('subtitles.avgScore') }}</span>
        </div>
        <div class="sub-stat-card glass-card">
          <span class="sub-stat-value">{{ stats.avg_daily }}</span>
          <span class="sub-stat-label">{{ $t('subtitles.avgDownloads') }}</span>
        </div>
        <div v-if="quota" class="sub-stat-card glass-card">
          <span class="sub-stat-value">{{ quota.remaining_downloads }}/{{ quota.allowed_downloads }}</span>
          <span class="sub-stat-label">{{ $t('subtitles.downloadsLeft') }}</span>
        </div>
      </div>

      <!-- Coverage by language -->
      <div class="glass-card sub-stat-section">
        <h3 class="sub-stat-title">{{ $t('subtitles.coverageByLang') }}</h3>
        <div v-if="stats.library_coverage" class="sub-stat-coverage">
          <SubCoverageBar
            v-for="(count, lang) in stats.by_language" :key="lang"
            :label="lang.toUpperCase()"
            :percentage="Math.round((count / Math.max(stats.total_downloads, 1)) * 100)"
          />
        </div>
        <div v-else class="sub-stat-empty">{{ $t('subtitles.noHistory') }}</div>
      </div>

      <!-- Download chart (last 30 days) -->
      <div class="glass-card sub-stat-section">
        <h3 class="sub-stat-title">{{ $t('subtitles.downloadChart') }}</h3>
        <div v-if="Object.keys(stats.daily || {}).length" class="sub-chart">
          <div v-for="(count, day) in stats.daily" :key="day" class="sub-chart-bar-wrap" :title="`${day}: ${count}`">
            <div class="sub-chart-bar" :style="{ height: barHeight(count) + '%' }" />
            <span class="sub-chart-label">{{ formatDay(day) }}</span>
          </div>
        </div>
        <div v-else class="sub-stat-empty">{{ $t('subtitles.noHistory') }}</div>
      </div>

      <!-- Score distribution -->
      <div class="glass-card sub-stat-section">
        <h3 class="sub-stat-title">{{ $t('subtitles.qualityScore') }}</h3>
        <div v-if="stats.score_distribution" class="sub-score-dist">
          <div v-for="(count, bucket) in stats.score_distribution" :key="bucket" class="sub-score-row">
            <span class="sub-score-label">{{ bucket }}★</span>
            <div class="sub-score-bar">
              <div class="sub-score-fill" :style="{ width: scoreBarWidth(count) + '%' }" />
            </div>
            <span class="sub-score-count">{{ count }}</span>
          </div>
        </div>
      </div>

      <!-- Source distribution -->
      <div v-if="Object.keys(stats.by_source || {}).length > 0" class="glass-card sub-stat-section">
        <h3 class="sub-stat-title">{{ $t('subtitles.source') }}</h3>
        <div class="sub-source-list">
          <div v-for="(count, source) in stats.by_source" :key="source" class="sub-source-row">
            <span class="sub-source-name">{{ source }}</span>
            <span class="sub-source-count">{{ count }}</span>
          </div>
        </div>
      </div>

    </template>

    <!-- Empty -->
    <MkEmptyState v-else :title="$t('subtitles.noHistory')" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useApi } from '@/composables/useApi'
import { useSubtitles } from '@/composables/useSubtitles'
import SubCoverageBar from './SubCoverageBar.vue'
import MkEmptyState from '@/components/common/MkEmptyState.vue'

const { apiGet } = useApi()
const { quota } = useSubtitles()

const stats = ref(null)
const loading = ref(false)
const loaded = ref(false)

async function loadStats() {
  if (loaded.value) return
  loading.value = true
  try {
    stats.value = await apiGet('/api/subtitles/statistics')
  } catch { /* silent: stats fetch, panel shows empty state */ }
  loading.value = false
  loaded.value = true
}

defineExpose({ loadStats })

const maxDaily = computed(() => {
  if (!stats.value?.daily) return 1
  return Math.max(...Object.values(stats.value.daily), 1)
})

const maxScore = computed(() => {
  if (!stats.value?.score_distribution) return 1
  return Math.max(...Object.values(stats.value.score_distribution), 1)
})

function barHeight(count) {
  return Math.round((count / maxDaily.value) * 100)
}

function scoreBarWidth(count) {
  return Math.round((count / maxScore.value) * 100)
}

function formatDay(day) {
  const d = new Date(day)
  return `${d.getDate()}/${d.getMonth() + 1}`
}

// Le loading est declenche par le parent via loadStats()
</script>

<style scoped>
.sub-center { display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 60px; gap: 12px; }

.sub-stat-cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 8px; margin-bottom: 16px; }
.sub-stat-card { display: flex; flex-direction: column; align-items: center; padding: 16px 12px; gap: 4px; }
.sub-stat-value { font-size: var(--text-lg); font-weight: var(--font-bold); color: var(--text-primary); }
.sub-stat-label { font-size: var(--text-3xs); color: var(--text-muted); text-transform: uppercase; letter-spacing: .3px; }

.sub-stat-section { padding: 16px; margin-bottom: 12px; }
.sub-stat-title { font-size: var(--text-2xs); font-weight: var(--font-medium); color: var(--text-muted); margin: 0 0 12px; text-transform: uppercase; letter-spacing: .3px; }
.sub-stat-coverage { display: flex; flex-direction: column; gap: 8px; }

.sub-chart { display: flex; align-items: flex-end; gap: 3px; height: 80px; padding-top: 8px; }
.sub-chart-bar-wrap { flex: 1; max-width: 28px; display: flex; flex-direction: column; align-items: center; height: 100%; justify-content: flex-end; }
.sub-chart-bar { width: 100%; min-height: 2px; background: var(--accent-500); border-radius: 3px 3px 0 0; transition: height var(--duration-slow); }
.sub-chart-label { font-size: var(--text-3xs); color: var(--text-muted); margin-top: 6px; white-space: nowrap; }

.sub-score-dist { display: flex; flex-direction: column; gap: 6px; }
.sub-score-row { display: flex; align-items: center; gap: 8px; }
.sub-score-label { font-size: var(--text-3xs); font-weight: var(--font-medium); color: var(--color-warning); min-width: 24px; }
.sub-score-bar { flex: 1; height: 6px; border-radius: 3px; background: var(--surface-3); overflow: hidden; }
.sub-score-fill { height: 100%; border-radius: 3px; background: var(--color-warning); transition: width var(--duration-slow); }
.sub-score-count { font-size: .58rem; color: var(--text-muted); min-width: 20px; text-align: right; }

.sub-source-list { display: flex; flex-direction: column; gap: 4px; }
.sub-source-row { display: flex; justify-content: space-between; padding: 6px 8px; background: rgba(255,255,255,.02); border-radius: var(--radius-btn); }
.sub-source-name { font-size: var(--text-2xs); color: var(--text-primary); text-transform: capitalize; }
.sub-source-count { font-size: var(--text-2xs); font-weight: var(--font-medium); color: var(--text-muted); }

.glass-card { background: var(--surface-1); backdrop-filter: blur(16px); border: .5px solid var(--border-default); border-radius: var(--radius-card); }
</style>
