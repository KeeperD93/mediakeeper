<template>
  <div>
    <div class="section-head">
      <h2 class="section-title">{{ $t('stats.playbackStats') }}</h2>
      <div class="period-pills">
        <button
          v-for="d in periodOptions"
          :key="d"
          class="pill"
          :class="{ active: playbackDays === d }"
          @click="changePlaybackDays(d)"
        >
          {{ d }}j
        </button>
        <button class="pill" :class="{ active: playbackDays === 0 }" @click="changePlaybackDays(0)">
          {{ $t('common.all') }}
        </button>
        <button
          class="pill pill-customize"
          :class="{ active: customizeMode }"
          @click="customizeMode = !customizeMode"
        >
          <SlidersHorizontal :size="11" />
          {{ customizeMode ? $t('dashboard.done') : $t('dashboard.customize') }}
        </button>
      </div>
    </div>
    <div v-if="!playback && loadingPlayback" class="top-grid">
      <div v-for="n in 9" :key="n" class="glass-card top-card-skel">
        <div class="skel-line w50 skel-line-mb12" />
        <div class="skel-line w70" />
        <div class="skel-line w40" />
      </div>
    </div>
    <div v-show="playback" class="top-grid">
      <div
        v-for="(card, ci) in orderedCards"
        :key="card.id"
        class="glass-card top-card"
        :class="{ 'drag-over': dragOverIdx === ci, dragging: customizeMode && dragIdx === ci }"
        :draggable="customizeMode"
        @dragstart="onDragStart(ci, $event)"
        @dragover.prevent="onDragOver(ci)"
        @dragend="onDragEnd"
        @drop.prevent="onDrop(ci)"
      >
        <div v-if="customizeMode" class="drag-handle">
          <GripVertical :size="12" fill="currentColor" />
        </div>
        <PlaybackCardDonut v-if="card.type === 'donut'" :by-method="playback?.by_method || []" />
        <PlaybackCardRadar
          v-else-if="card.type === 'genre'"
          :by-genre="playback?.by_genre || []"
        />
        <PlaybackCardRank
          v-else
          :card="card"
          :show-preview="showPreview"
          :hide-preview="hidePreview"
          :open-user-profile="openUserProfile"
          :go-to-activity-search="goToActivitySearch"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useStats } from '@/composables/useStats'
import { GripVertical, SlidersHorizontal } from 'lucide-vue-next'
import { useStatsUI } from '@/composables/useStatsUI'
import PlaybackCardDonut from './StatsPlaybackCards/PlaybackCardDonut.vue'
import PlaybackCardRadar from './StatsPlaybackCards/PlaybackCardRadar.vue'
import PlaybackCardRank from './StatsPlaybackCards/PlaybackCardRank.vue'
import { usePlaybackCards } from './StatsPlaybackCards/usePlaybackCards'

const { t } = useI18n()
const { playback, loadingPlayback, loadPlayback, resolveSeriesImageId, ticksToHours } = useStats()
const { showPreview, hidePreview, openUserProfile, goToActivitySearch } = useStatsUI()

const periodOptions = [7, 30, 90, 180, 365]
const playbackDays = ref(365)

function changePlaybackDays(d) {
  playbackDays.value = d
  loadPlaybackAndResolve(d)
}
async function loadPlaybackAndResolve(days) {
  await loadPlayback(days)
  if (!playback.value) return
  for (const k of ['top_series', 'popular_series'])
    for (const it of playback.value[k] || [])
      if (it.name && !it.series_id) it.series_id = await resolveSeriesImageId(it.name)
}
// Initial load triggered from parent GeneralTab
defineExpose({ loadPlaybackAndResolve })

const {
  customizeMode,
  orderedCards,
  dragIdx,
  dragOverIdx,
  onDragStart,
  onDragOver,
  onDragEnd,
  onDrop,
} = usePlaybackCards(playback, t, ticksToHours)
</script>

<style scoped>
.section-head {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
  margin-top: 28px;
}
.section-title {
  font-size: var(--text-base);
  font-weight: var(--font-medium);
  color: var(--text-primary);
  margin: 0;
}

.top-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}
.glass-card {
  background: var(--surface-1);
  backdrop-filter: var(--blur-md);
  border: 0.5px solid var(--border-default);
  border-radius: var(--radius-card);
}
.top-card {
  padding: 14px 16px;
}

.pill-customize {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.drag-handle {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2px 0 4px;
  color: rgb(255, 255, 255, 0.2);
  cursor: grab;
}
.drag-handle:active {
  cursor: grabbing;
}
.dragging {
  opacity: 0.5;
  border: 1px dashed rgb(var(--accent-rgb), 0.4) !important;
}
.drag-over {
  border-color: var(--accent-500) !important;
  box-shadow:
    0 0 0 1px var(--accent-500),
    0 0 16px rgb(var(--accent-rgb), 0.15);
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
  animation: pc-sk var(--duration-animation) ease-in-out infinite;
}
.w40 {
  width: 40%;
}
.w50 {
  width: 50%;
}
.w70 {
  width: 70%;
}
@keyframes pc-sk {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}
.top-card-skel {
  padding: 14px 16px;
}
.skel-line-mb12 {
  margin-bottom: 12px;
}

@media (max-width: 1280px) {
  .top-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@media (max-width: 768px) {
  .top-grid {
    grid-template-columns: 1fr;
  }
}
</style>
