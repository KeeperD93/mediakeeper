<template>
  <div class="sub-panel">

    <!-- ═══ Filters ═══ -->
    <div class="sf-bar">
      <!-- Group 1 — content filters (what data is shown) -->
      <div class="sf-group sf-group--filters">
        <div class="sf-search-wrap">
          <span class="sf-search-icon">&#8981;</span>
          <input v-model="libSearch" class="sf-search" :placeholder="$t('subtitles.searchLibrary')" @input="debounceLibrary" />
        </div>
        <select v-model="libType" class="sf-select" @change="resetLibrary">
          <option value="Movie,Episode">{{ $t('subtitles.typeAll') }}</option>
          <option value="Movie">{{ $t('subtitles.typeMovie') }}</option>
          <option value="Episode">{{ $t('subtitles.typeSeries') }}</option>
        </select>
        <select v-model="libLibrary" class="sf-select" @change="resetLibrary">
          <option value="">{{ $t('subtitles.allLibraries') }}</option>
          <option v-for="lib in embyLibraries" :key="lib.id" :value="lib.id">{{ lib.name }}</option>
        </select>
      </div>

      <div class="sf-divider" aria-hidden="true"></div>

      <!-- Group 2 — subtitle status filter -->
      <div class="sf-group sf-group--status sf-status-btns">
        <button class="sf-status-btn" :class="{ active: libStatus === '' }" @click="libStatus = ''; resetLibrary()">
          {{ $t('subtitles.filterAll') }}
        </button>
        <button class="sf-status-btn" :class="{ active: libStatus === 'missing' }" @click="libStatus = 'missing'; resetLibrary()">
          <AlertCircle :size="12" />
          {{ $t('subtitles.filterMissing') }}
        </button>
        <button class="sf-status-btn" :class="{ active: libStatus === 'complete' }" @click="libStatus = 'complete'; resetLibrary()">
          <Check :size="12" />
          {{ $t('subtitles.filterComplete') }}
        </button>
      </div>

      <div class="sf-divider" aria-hidden="true"></div>

      <!-- Group 3 — tools and view -->
      <div class="sf-group sf-group--tools">
        <button class="sf-tool-btn" :title="$t('subtitles.audit')" @click="$emit('audit')">
          <ClipboardCheck :size="14" />
        </button>
        <button class="sf-tool-btn" :class="{ active: selectMode }" :title="$t('subtitles.selectMode')" @click="toggleSelectMode">
          <CheckSquare :size="14" />
        </button>
        <div class="sf-view-toggle">
          <button class="sf-view-btn" :class="{ active: viewMode === 'grid' }" :title="$t('subtitles.gridView')" @click="viewMode = 'grid'">
            <LayoutGrid :size="14" />
          </button>
          <button class="sf-view-btn" :class="{ active: viewMode === 'list' }" :title="$t('subtitles.listView')" @click="viewMode = 'list'">
            <List :size="14" />
          </button>
        </div>
      </div>
    </div>

    <SubBatchPanel v-if="selectMode" :selected-items="selectedItems" :batch-running="batchRunning"
      @start="startBatch" @clear="selectedItems = []" @cancel="cancelBatch" />

    <SubSeriesMatrix v-if="matrixData" :matrix-data="matrixData" :loading="matrixLoading"
      @close="matrixData = null" @select-episode="onMatrixEpisodeClick" />

    <div v-if="libLoading && !libraryItems.length" class="sub-center"><span class="mk-spin mk-spin-24" /></div>

    <template v-else-if="displayItems.length">
      <div :class="viewMode === 'grid' ? 'sg-grid' : 'sl-list'">
        <SubLibraryItem
          v-for="item in displayItems" :key="item._groupKey || item.item_id"
          :item="item"
          :mode="viewMode"
          :expanded="!item._isGroup && expandedId === item.item_id"
          :subs="!item._isGroup && expandedId === item.item_id ? itemSubs : null"
          :results="!item._isGroup && expandedId === item.item_id ? itemResults : []"
          :searching="!item._isGroup && expandedId === item.item_id && itemSearching"
          :downloading-id="downloading"
          :os-count="getOsCount(item.imdb_id || item.tmdb_id)"
          :last-download-result="!item._isGroup && expandedId === item.item_id ? lastDownloadResult : null"
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

      <div v-if="totalPages > 1" class="sp-pagination">
        <button class="sp-btn" :disabled="currentPage <= 1" @click="goToPage(currentPage - 1)">
          <ChevronLeft :size="14" />
        </button>
        <button v-for="p in visiblePages" :key="p" class="sp-btn" :class="{ active: p === currentPage, dots: p === '...' }" :disabled="p === '...'" @click="p !== '...' && goToPage(p)">
          {{ p }}
        </button>
        <button class="sp-btn" :disabled="currentPage >= totalPages" @click="goToPage(currentPage + 1)">
          <ChevronRight :size="14" />
        </button>
        <span class="sp-info">{{ libraryTotal }} {{ $t('subtitles.results') }}</span>
      </div>
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

    <SubItemOverlay v-if="itemOverlay" :visible="true" :item="itemOverlay" @close="itemOverlay = null" @downloaded="loadPage()" />

    <SubComparatorModal :visible="showComparator" :file-a="compareFiles[0] || null" :file-b="compareFiles[1] || null" @close="showComparator = false" />
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
import { AlertCircle, Check, CheckSquare, ChevronLeft, ChevronRight, ClipboardCheck, Film, LayoutGrid, List } from 'lucide-vue-next'
import MkEmptyState from '@/components/common/MkEmptyState.vue'

const emit = defineEmits(['update-missing', 'audit'])

const { embyLibraries, getOsCount } = useSubtitles()

const {
  libraryItems, libraryTotal, libLoading,
  libSearch, libType, libLibrary, libStatus, viewMode, currentPage,
  expandedId, itemSubs, itemAudio, itemResults, itemSearching, downloading, lastDownloadResult,
  matrixData, matrixLoading, compareFiles, showComparator,
  selectMode, selectedItems, batchRunning, seriesOverlay, itemOverlay,
  displayItems, totalPages, visiblePages,
  goToPage, loadPage, resetLibrary, debounceLibrary,
  onItemClick, onOverlayEpisodeSelect,
  searchForItem, downloadForItem, deleteSubtitle, removeStream,
  toggleSelectMode, toggleItemSelect, startBatch, cancelBatch,
  openComparator, showMatrix, onMatrixEpisodeClick,
} = useSubLibrary(emit)

defineExpose({ resetLibrary })
</script>

<style scoped>
/* Filter bar — three logical groups separated by thin dividers.
   Group 1: content filters (search + type + library)
   Group 2: subtitle status pills
   Group 3: tools (audit, batch select) + view toggle */
.sf-bar { display: flex; align-items: center; gap: 12px; padding: 0 0 16px; flex-wrap: wrap; row-gap: 10px; }
.sf-group { display: flex; align-items: center; gap: 8px; }
.sf-group--filters { flex: 1 1 auto; min-width: 0; }
.sf-group--status { flex: 0 0 auto; }
.sf-group--tools { flex: 0 0 auto; }
.sf-divider { flex: 0 0 auto; width: 1px; height: 24px; background: var(--border-subtle); align-self: center; }

.sf-search-wrap { flex: 1 1 auto; position: relative; min-width: 180px; max-width: 360px; }
.sf-search-icon { position: absolute; left: 14px; top: 50%; transform: translateY(-50%); font-size: var(--text-base); color: rgba(255,255,255,.2); }
.sf-search {
  width: 100%; padding: 11px 14px 11px 38px; border: 1px solid var(--border-default);
  border-radius: var(--radius-card); font-size: var(--text-sm); font-family: inherit; box-sizing: border-box;
  background: rgba(255,255,255,.03); color: var(--text-primary); outline: none;
}
.sf-search:focus { border-color: rgba(var(--accent-rgb),.3); }
.sf-search::placeholder { color: rgba(255,255,255,.2); }
.sf-select {
  padding: 10px 12px; border-radius: var(--radius-input); font-size: var(--text-2xs); font-family: inherit; cursor: pointer;
  background: rgba(255,255,255,.02); border: 1px solid var(--border-default);
  color: var(--text-primary); outline: none;
}
.sf-select option { background: var(--bg-secondary); color: var(--text-primary); }
.sf-status-btns { gap: 2px; }
.sf-status-btn {
  padding: 9px 16px; border-radius: var(--radius-input); font-size: var(--text-2xs); font-weight: var(--font-regular);
  font-family: inherit; cursor: pointer; transition: all var(--duration-base);
  border: 1px solid var(--border-default); background: rgba(255,255,255,.02); color: var(--text-faint);
  display: inline-flex; align-items: center; gap: 5px;
}
.sf-status-btn.active { border-color: rgba(var(--accent-rgb),.3); background: rgba(var(--accent-rgb),.1); color: var(--accent-300); }
.sf-tool-btn {
  width: 38px; height: 38px; border-radius: var(--radius-input); display: flex; align-items: center; justify-content: center;
  background: rgba(255,255,255,.02); border: 1px solid var(--border-default);
  color: rgba(255,255,255,.3); cursor: pointer; transition: all var(--duration-base);
}
.sf-tool-btn.active { background: rgba(var(--accent-rgb),.1); color: var(--accent-300); border-color: rgba(var(--accent-rgb),.3); }
.sf-view-toggle { display: flex; gap: 2px; background: rgba(255,255,255,.03); border-radius: var(--radius-btn); padding: 2px; }
.sf-view-btn {
  width: 34px; height: 30px; border: none; border-radius: var(--radius-sm); cursor: pointer;
  background: transparent; color: rgba(255,255,255,.2);
  display: flex; align-items: center; justify-content: center; transition: all var(--duration-base);
}
.sf-view-btn.active { background: rgba(255,255,255,.08); color: var(--text-primary); }

.sg-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(155px, 1fr)); gap: 12px; padding-bottom: 8px; }
.sl-list { display: flex; flex-direction: column; gap: 2px; padding-bottom: 8px; }
.sg-animated { animation: fadeUp .4s ease both; }
@keyframes fadeUp { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: translateY(0); } }

.sp-pagination { display: flex; align-items: center; justify-content: center; gap: 4px; padding: 16px 0 8px; }
.sp-btn {
  min-width: 34px; height: 34px; border-radius: var(--radius-btn); display: flex; align-items: center; justify-content: center;
  font-size: var(--text-xs); font-weight: var(--font-regular); font-family: inherit; cursor: pointer; transition: all var(--duration-base);
  border: 1px solid var(--border-default); background: rgba(255,255,255,.02); color: var(--text-faint);
}
.sp-btn:hover:not(:disabled):not(.dots) { background: var(--surface-3); color: var(--text-primary); }
.sp-btn.active { background: rgba(var(--accent-rgb),.15); color: var(--accent-300); border-color: rgba(var(--accent-rgb),.3); }
.sp-btn:disabled { opacity: .3; cursor: default; }
.sp-btn.dots { border: none; background: none; cursor: default; color: rgba(255,255,255,.2); }
.sp-info { font-size: var(--text-3xs); color: var(--text-muted); margin-left: 12px; }

.sub-center { display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 60px; gap: 12px; }

/* ═══ Mobile (≤ 767px) — each group becomes a full-width row ═══
   Dividers are hidden; groups already carry enough visual grouping
   through spacing and the row break. All interactive controls meet
   the 44 × 44 px touch-target convention. */
@media (max-width: 767px) {
  .sf-bar { gap: 8px; row-gap: 10px; }
  .sf-divider { display: none; }

  /* Group 1 — content filters: search on its own line, both selects share the next one. */
  .sf-group--filters { flex: 1 1 100%; flex-wrap: wrap; gap: 8px; }
  .sf-search-wrap { flex: 1 1 100%; min-width: 0; max-width: none; }
  .sf-search { min-height: 44px; }
  .sf-select { flex: 1 1 calc(50% - 4px); min-width: 0; min-height: 44px; }

  /* Group 2 — status pills spread evenly across a full row. */
  .sf-group--status { flex: 1 1 100%; gap: 4px; }
  .sf-status-btn { flex: 1 1 0; min-width: 0; min-height: 44px; justify-content: center; padding: 8px 6px; }

  /* Group 3 — tools cluster, pushed to the right of its row. */
  .sf-group--tools { flex: 1 1 100%; justify-content: flex-end; }
  .sf-tool-btn { min-width: 44px; min-height: 44px; }
  .sf-view-btn { width: auto; height: auto; min-width: 44px; min-height: 44px; }
}
</style>
