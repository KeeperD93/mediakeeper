<template>
  <div class="sub-panel">
    <SubLibraryFilterBar
      v-model:lib-search="libSearch"
      v-model:lib-type="libType"
      v-model:lib-library="libLibrary"
      v-model:lib-status="libStatus"
      v-model:view-mode="viewMode"
      :select-mode="selectMode"
      :emby-libraries="embyLibraries"
      @reset-library="resetLibrary"
      @debounce-library="debounceLibrary"
      @toggle-select-mode="toggleSelectMode"
      @audit="$emit('audit')"
    />

    <SubBatchPanel
      v-if="selectMode"
      :selected-items="selectedItems"
      :batch-running="batchRunning"
      @start="startBatch"
      @clear="selectedItems = []"
      @cancel="cancelBatch"
    />

    <SubSeriesMatrix
      v-if="matrixData"
      :matrix-data="matrixData"
      :loading="matrixLoading"
      @close="matrixData = null"
      @select-episode="onMatrixEpisodeClick"
    />

    <div v-if="libLoading && !libraryItems.length" class="sub-center">
      <span class="mk-spin mk-spin-24" />
    </div>

    <template v-else-if="displayItems.length">
      <div :class="viewMode === 'grid' ? 'sg-grid' : 'sl-list'">
        <SubLibraryItem
          v-for="item in displayItems"
          :key="item._groupKey || item.item_id"
          :item="item"
          :mode="viewMode"
          :expanded="!item._isGroup && expandedId === item.item_id"
          :subs="!item._isGroup && expandedId === item.item_id ? itemSubs : null"
          :results="!item._isGroup && expandedId === item.item_id ? itemResults : []"
          :searching="!item._isGroup && expandedId === item.item_id && itemSearching"
          :downloading-id="downloading"
          :os-count="getOsCount(item.imdb_id || item.tmdb_id)"
          :last-download-result="
            !item._isGroup && expandedId === item.item_id ? lastDownloadResult : null
          "
          :audio-streams="!item._isGroup && expandedId === item.item_id ? itemAudio : []"
          :selectable="selectMode"
          :is-selected="selectedItems.some(s => s.emby_item_id === item.item_id)"
          @toggle="onItemClick(item)"
          @search="searchForItem(item)"
          @download="downloadForItem($event, item)"
          @delete-sub="deleteSubtitle($event)"
          @show-matrix="showMatrix($event)"
          @compare="openComparator($event)"
          @select-item="toggleItemSelect(item)"
          @remove-stream="removeStream($event)"
        />
      </div>

      <SubLibraryPagination
        :current-page="currentPage"
        :total-pages="totalPages"
        :visible-pages="visiblePages"
        :library-total="libraryTotal"
        @go-to="goToPage"
      />
    </template>

    <MkEmptyState v-else-if="!libLoading" :icon="Film" :title="$t('subtitles.noItems')" />

    <SubSeriesOverlay
      :visible="!!seriesOverlay"
      :series-name="seriesOverlay?.seriesName || ''"
      :series-poster="seriesOverlay?.posterId || ''"
      :episodes="seriesOverlay?.episodes || []"
      @close="seriesOverlay = null"
      @select-episode="onOverlayEpisodeSelect"
      @downloaded="loadPage()"
    />

    <SubItemOverlay
      v-if="itemOverlay"
      :visible="true"
      :item="itemOverlay"
      @close="itemOverlay = null"
      @downloaded="loadPage()"
    />

    <SubComparatorModal
      :visible="showComparator"
      :file-a="compareFiles[0] || null"
      :file-b="compareFiles[1] || null"
      @close="showComparator = false"
    />
  </div>
</template>

<script setup>
import { useSubtitles } from '@/composables/useSubtitles'
import { useSubLibrary } from '@/composables/useSubLibrary'
import SubLibraryItem from './SubLibraryItem.vue'
import SubSeriesMatrix from './SubSeriesMatrix.vue'
import SubSeriesOverlay from './SubSeriesOverlay.vue'
import SubItemOverlay from './SubItemOverlay.vue'
import SubComparatorModal from './SubComparatorModal.vue'
import SubBatchPanel from './SubBatchPanel.vue'
import SubLibraryFilterBar from './library/SubLibraryFilterBar.vue'
import SubLibraryPagination from './library/SubLibraryPagination.vue'
import { Film } from 'lucide-vue-next'
import MkEmptyState from '@/components/common/MkEmptyState.vue'

const emit = defineEmits(['update-missing', 'audit'])

const { embyLibraries, getOsCount } = useSubtitles()

const {
  libraryItems,
  libraryTotal,
  libLoading,
  libSearch,
  libType,
  libLibrary,
  libStatus,
  viewMode,
  currentPage,
  expandedId,
  itemSubs,
  itemAudio,
  itemResults,
  itemSearching,
  downloading,
  lastDownloadResult,
  matrixData,
  matrixLoading,
  compareFiles,
  showComparator,
  selectMode,
  selectedItems,
  batchRunning,
  seriesOverlay,
  itemOverlay,
  displayItems,
  totalPages,
  visiblePages,
  goToPage,
  loadPage,
  resetLibrary,
  debounceLibrary,
  onItemClick,
  onOverlayEpisodeSelect,
  searchForItem,
  downloadForItem,
  deleteSubtitle,
  removeStream,
  toggleSelectMode,
  toggleItemSelect,
  startBatch,
  cancelBatch,
  openComparator,
  showMatrix,
  onMatrixEpisodeClick,
} = useSubLibrary(emit)

defineExpose({ resetLibrary })
</script>

<style scoped>
.sg-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(clamp(108px, 30vw, 120px), 1fr));
  gap: 6px;
  padding-bottom: 8px;
}
@media (min-width: 768px) {
  .sg-grid {
    grid-template-columns: repeat(auto-fill, minmax(155px, 1fr));
    gap: 12px;
  }
}
.sl-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding-bottom: 8px;
}
.sg-animated {
  animation: fade-up 0.4s ease both;
}
@keyframes fade-up {
  from {
    opacity: 0;
    transform: translateY(12px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.sub-center {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px;
  gap: 12px;
}
</style>
