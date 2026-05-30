<template>
  <div class="mm-col">
    <div class="mm-col-header">
      <div class="mm-bc">
        <span class="mm-crumb" @click="navRoot">
          <Folder :size="12" />
          {{ CATS.find(c => c.key === activeCat)?.label }}
        </span>
        <template v-for="(seg, i) in breadcrumbs" :key="i">
          <span class="mm-sep">/</span>
          <span class="mm-crumb" @click="navTo(i)">{{ seg }}</span>
        </template>
      </div>
      <div class="mm-header-actions">
        <button
          v-if="subPath"
          class="mm-btn-sm"
          :title="$t('mediaManager.rename')"
          @click="openRenameFolderModal"
        >
          <Pencil />
          {{ $t('mediaManager.rename') }}
        </button>
        <span class="mm-count">
          {{ $t('mediaManager.files_n', { dirs: fileCount.dirs || 0, vids: fileCount.vids }) }}
        </span>
      </div>
    </div>

    <MMToolbar
      v-model:filter-query="filterQuery"
      v-model:show-quality-score="showQualityScore"
      :sort-mode="sortMode"
      :analysis-active="analysisActive"
      :issues-count="issuesCount"
      :extraction-running="extractionRunning"
      :checked="checked"
      :filtered="filtered"
      :new-files-count="newFilesCount"
      :checked-dirs="checkedDirs"
      :sub-path="subPath"
      :can-move-multi="canMoveMulti"
      @toggle-all="toggleAll"
      @cycle-sort-name="cycleSortName"
      @cycle-sort-size="cycleSortSize"
      @analyze-names="analyzeNames"
      @clear-analysis="clearAnalysis"
      @show-history="showHistoryModal = true"
      @show-move-history="onShowMoveHistory"
      @delete-selected="deleteSelected"
      @load-files="loadFiles"
      @extract-subfolders="extractFromSubfolders"
      @open-move-multi="openMoveModalMulti"
      @update:filter-query="applyFilter"
    />

    <div ref="fileListRef" class="mm-file-list" @scroll="onScroll">
      <div v-if="lassoDragging" class="mm-lasso" :style="lassoStyle" />
      <div v-if="loading" class="mm-state">
        <MkSpinner size="sm" />
        <span>{{ $t('mediaManager.loading') }}</span>
      </div>
      <div v-else-if="!filtered.length" class="mm-state">
        <span>{{ $t('mediaManager.noFiles') }}</span>
      </div>
      <template v-else>
        <div v-if="!newNames.length" :style="{ height: vsTop + 'px' }" />
        <MMFileRow
          v-for="(f, vi) in newNames.length ? filtered : vsItems"
          :key="f.path"
          :f="f"
          :is-checked="checked.has(newNames.length ? vi : vi + vsStart)"
          :is-drop-target="dragOverFolder === (newNames.length ? vi : vi + vsStart)"
          :expanded-mode="expandedMode"
          :multi-cat-mode="multiCatMode"
          :analysis-active="analysisActive"
          :naming-issues="namingIssues"
          :show-quality-score="showQualityScore"
          :get-file-cat="getFileCat"
          :is-file-new="isFileNew"
          :compute-quality-score="computeQualityScore"
          :get-quality-color="getQualityColor"
          @row-click="rowClick($event, newNames.length ? vi : vi + vsStart, f)"
          @row-ctx="openCtxMenu($event, newNames.length ? vi : vi + vsStart, f)"
          @drag-start="fileDragStart(newNames.length ? vi : vi + vsStart)"
          @drag-end="fileDragEnd"
          @drag-over="dragOverFolder = newNames.length ? vi : vi + vsStart"
          @drag-leave="dragOverFolder = null"
          @drop="(dropOnFolder(newNames.length ? vi : vi + vsStart), (dragOverFolder = null))"
          @quality-enter="showQualityPopup($event, f)"
          @quality-leave="hideQualityPopup"
          @open-meta="openFileMeta(f)"
          @open-move="openMoveModal(newNames.length ? vi : vi + vsStart)"
          @delete-file="deleteFile(newNames.length ? vi : vi + vsStart)"
        />
        <div v-if="!newNames.length" :style="{ height: vsBottom + 'px' }" />
      </template>
    </div>

    <MMQualityPopup :quality-popup="qualityPopup" :get-quality-color="getQualityColor" />

    <MMCtxMenu
      :ctx-menu="ctxMenu"
      :inline-rename="inlineRename"
      :set-rename-input="setRenameInput"
      @ctx-rename="ctxRename"
      @ctx-move="ctxMove"
      @ctx-info="ctxInfo"
      @ctx-delete="ctxDelete"
      @submit-rename="submitInlineRename"
      @close-rename="inlineRename.show = false"
      @update:rename-value="inlineRename.value = $event"
    />
  </div>
</template>

<script setup>
import { ref, computed, inject } from 'vue'
import { useMediaManager, CATS } from '@/composables/useMediaManager'
import { useMMFileListUI } from '@/composables/useMMFileListUI'
import { Folder, Pencil } from 'lucide-vue-next'
import { FILE_TYPE } from '@/constants/mediaManager'
import MkSpinner from '@/components/common/MkSpinner.vue'
import MMToolbar from './MMFileList/MMToolbar.vue'
import MMFileRow from './MMFileList/MMFileRow.vue'
import MMQualityPopup from './MMFileList/MMQualityPopup.vue'
import MMCtxMenu from './MMFileList/MMCtxMenu.vue'

const {
  activeCat,
  subPath,
  filtered,
  checked,
  loading,
  filterQuery,
  sortMode,
  expandedMode,
  newNames,
  breadcrumbs,
  fileCount,
  canMoveMulti,
  newFilesCount,
  issuesCount,
  namingIssues,
  analysisActive,
  multiCatMode,
  navRoot,
  navTo,
  loadFiles,
  applyFilter,
  sortLeft,
  toggleAll,
  toggleCheck,
  deleteFile,
  deleteSelected,
  getFileCat,
  isFileNew,
  fileDragStart,
  fileDragEnd,
  dropOnFolder,
  openMoveModal,
  openMoveModalMulti,
  openRenameFolderModal,
  extractFromSubfolders,
  extractionRunning,
  cancelExtraction,
  checkedDirs,
  analyzeNames,
  clearAnalysis,
  computeQualityScore,
  getQualityColor,
  openFileMeta,
  showMoveHistoryModal,
  enterDir,
} = useMediaManager()

const { showHistoryModal } = inject('mmCtx')

const dragOverFolder = ref(null)
const showQualityScore = ref(false)
const lastCheckedIdx = ref(null)
const fileListRef = ref(null)

const ROW_H = 36
const BUFFER = 20
const vsScrollTop = ref(0)
const vsStart = computed(() => Math.max(0, Math.floor(vsScrollTop.value / ROW_H) - BUFFER))
const vsEnd = computed(() => {
  const viewH = fileListRef.value?.clientHeight || 600
  return Math.min(filtered.value.length, Math.ceil((vsScrollTop.value + viewH) / ROW_H) + BUFFER)
})
const vsItems = computed(() => filtered.value.slice(vsStart.value, vsEnd.value))
const vsTop = computed(() => vsStart.value * ROW_H)
const vsBottom = computed(() => Math.max(0, (filtered.value.length - vsEnd.value) * ROW_H))

const {
  lassoDragging,
  lassoStyle,
  ctxMenu,
  openCtxMenu,
  ctxRename,
  ctxMove,
  ctxInfo,
  ctxDelete,
  inlineRename,
  renameInputRef,
  submitInlineRename,
  qualityPopup,
  showQualityPopup,
  hideQualityPopup,
} = useMMFileListUI({ fileListRef, filtered, checked })

function setRenameInput(el) {
  renameInputRef.value = el
}

defineExpose({ fileListRef, vsScrollTop, newNames })

const emit = defineEmits(['scroll'])
let _scrollRaf = null
function onScroll(e) {
  if (_scrollRaf) cancelAnimationFrame(_scrollRaf)
  _scrollRaf = requestAnimationFrame(() => {
    vsScrollTop.value = e.target.scrollTop
    emit('scroll', e.target.scrollTop)
    _scrollRaf = null
  })
}

function cycleSortName() {
  sortLeft(sortMode.value === 'name-asc' ? 'name-desc' : 'name-asc')
}
function cycleSortSize() {
  sortLeft(sortMode.value === 'size-asc' ? 'size-desc' : 'size-asc')
}

function rowClick(e, i, f) {
  if (e.target.closest('.mm-row-btn')) return
  if (f.type === FILE_TYPE.FOLDER && e.detail === 2) {
    enterDir(f.name)
    return
  }
  if (e.shiftKey && lastCheckedIdx.value !== null) {
    const from = Math.min(lastCheckedIdx.value, i)
    const to = Math.max(lastCheckedIdx.value, i)
    const s = new Set(checked.value)
    for (let x = from; x <= to; x++) s.add(x)
    checked.value = s
  } else {
    lastCheckedIdx.value = i
    toggleCheck(i)
  }
}

function onShowMoveHistory() {
  if (extractionRunning.value) cancelExtraction()
  showMoveHistoryModal.value = true
}
</script>
