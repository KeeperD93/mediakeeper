<template>
  <div>
    <div class="wlsu-header">
      <div class="wlsu-section-label">
        {{ $t('watchlist.trackedCount', { count: tracked.length }) }}
      </div>
      <div class="wlsu-view-toggle">
        <button
          class="vt-btn"
          :class="{ active: viewMode === 'wall' }"
          :title="$t('watchlist.posterWall')"
          @click="viewMode = 'wall'"
        >
          <LayoutGrid :size="12" />
        </button>
        <button
          class="vt-btn"
          :class="{ active: viewMode === 'list' }"
          :title="$t('watchlist.listView')"
          @click="viewMode = 'list'"
        >
          <List :size="12" />
        </button>
      </div>
    </div>

    <p v-if="!tracked.length && viewMode === 'list'" class="wlsu-empty">
      {{ $t('watchlist.noTracked') }}
    </p>

    <WlSuiviWall
      v-if="viewMode === 'wall'"
      :tracked="tracked"
      @select="selected = $event"
      @untrack="toggleTrack"
      @open-add="openAddModal"
    />

    <div v-else class="wlsu-list-view">
      <WlMediaCard
        v-for="item in tracked"
        :key="item.tmdb_id + '_' + item.media_type"
        :item="item"
      />
      <div class="wlsu-add-list" @click="openAddModal">
        <Plus :size="14" />
        {{ $t('watchlist.addMovieOrSeries') }}
      </div>
    </div>

    <WlSuiviDetailModal
      :selected="selected"
      @close="selected = null"
      @untrack="(item) => { toggleTrack(item); selected = null }"
    />

    <WlSuiviAddModal
      :open="showAddModal"
      :is-tracked="isTracked"
      :search-tmdb="searchTMDB"
      @close="showAddModal = false"
      @toggle-track="toggleTrack"
    />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useWatchlist } from '@/composables/useWatchlist'
import WlMediaCard from './WlMediaCard.vue'
import WlSuiviWall from './WlSuiviView/WlSuiviWall.vue'
import WlSuiviDetailModal from './WlSuiviView/WlSuiviDetailModal.vue'
import WlSuiviAddModal from './WlSuiviView/WlSuiviAddModal.vue'
import { LayoutGrid, List, Plus } from 'lucide-vue-next'

const { tracked, searchTMDB, toggleTrack, isTracked } = useWatchlist()

const viewMode = ref('wall')
const selected = ref(null)
const showAddModal = ref(false)

function openAddModal() {
  showAddModal.value = true
}
</script>

<style scoped>
.wlsu-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}
.wlsu-section-label {
  font-size: var(--text-2xs);
  text-transform: uppercase;
  letter-spacing: 0.8px;
  color: var(--text-muted);
  font-weight: var(--font-medium);
}
.wlsu-empty {
  font-size: var(--text-base);
  color: var(--text-muted);
  text-align: center;
  padding: 60px;
}
.wlsu-view-toggle {
  display: flex;
  gap: 4px;
}
.vt-btn {
  width: 34px;
  height: 30px;
  border: 1px solid var(--border-strong);
  background: var(--surface-1);
  border-radius: var(--radius-pill);
  cursor: pointer;
  color: rgb(255, 255, 255, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.18s;
  backdrop-filter: var(--blur-xs);
  -webkit-tap-highlight-color: transparent;
}
@media (hover: hover) {
  .vt-btn:hover:not(.active) {
    border-color: rgb(255, 255, 255, 0.18);
    color: rgb(255, 255, 255, 0.85);
    transform: translateY(-1px);
  }
}
.vt-btn.active {
  background: var(--gradient-pill-active);
  border-color: var(--accent-500);
  color: var(--text-primary);
  box-shadow: var(--mk-pill-shadow-sm);
}

.wlsu-list-view {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.wlsu-add-list {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  border-radius: var(--radius-btn);
  border: 0.5px dashed rgb(255, 255, 255, 0.1);
  color: var(--text-muted);
  font-size: var(--text-sm);
  cursor: pointer;
  transition: all var(--duration-fast);
}
.wlsu-add-list:hover {
  border-color: rgb(99, 102, 241, 0.35);
  color: var(--accent-400);
}
</style>
