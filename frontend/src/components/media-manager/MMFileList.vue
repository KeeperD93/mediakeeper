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

    <div class="mm-toolbar">
      <label class="mm-chk-all-label" :title="$t('mediaManager.toggleAll')">
        <input
          type="checkbox"
          :checked="checked.size > 0 && checked.size === filtered.length"
          :indeterminate.prop="checked.size > 0 && checked.size < filtered.length"
          class="mm-chkbox"
          @change="e => toggleAll(e.target.checked)"
        />
      </label>
      <input
        v-model="filterQuery"
        :placeholder="$t('mediaManager.filterPlaceholder')"
        class="mm-filter"
        @input="applyFilter"
      />
      <div class="mm-sort-group" :title="$t('mediaManager.sortAlpha')">
        <button
          class="mm-btn-sm mm-sort-btn"
          :class="{ 'mm-btn-accent': sortMode.startsWith('name') }"
          @click="cycleSortName"
        >
          <ArrowDownAZ class="mm-ico-11" />
          <span>
            {{ sortMode === 'name-asc' ? 'A→Z' : sortMode === 'name-desc' ? 'Z→A' : 'A→Z' }}
          </span>
        </button>
      </div>
      <div class="mm-sort-group" :title="$t('mediaManager.sortSize')">
        <button
          class="mm-btn-sm mm-sort-btn"
          :class="{ 'mm-btn-accent': sortMode.startsWith('size') }"
          @click="cycleSortSize"
        >
          <ArrowDownUp class="mm-ico-11" />
          <span>
            {{ $t('mediaManager.sortSize') }}
            {{ sortMode === 'size-asc' ? '↑' : sortMode === 'size-desc' ? '↓' : '↑' }}
          </span>
        </button>
      </div>
      <button
        class="mm-btn-sm"
        :class="{ 'mm-btn-accent': showQualityScore }"
        :title="$t('mediaManager.qualityScoreTitle', { n: '' })"
        @click="showQualityScore = !showQualityScore"
      >
        <Star class="mm-ico-12" />
      </button>
      <button
        class="mm-btn-sm"
        :class="{ 'mm-btn-warn': analysisActive && issuesCount > 0 }"
        :title="$t('mediaManager.configuration')"
        @click="analysisActive ? clearAnalysis() : analyzeNames()"
      >
        <CircleCheck :size="12" />
        <span v-if="analysisActive && issuesCount > 0" class="mm-issue-count">
          {{ issuesCount }}
        </span>
      </button>
      <button
        class="mm-btn-sm"
        :title="$t('mediaManager.renameHistoryTitle')"
        @click="showHistoryModal = true"
      >
        <Pencil :size="12" />
        <RotateCw :size="10" class="mm-ico-overlap" />
      </button>
      <button
        class="mm-btn-sm"
        :class="{ 'mm-btn-warn': extractionRunning }"
        :title="
          extractionRunning
            ? $t('mediaManager.cancelExtraction')
            : $t('mediaManager.moveHistoryTitle')
        "
        @click="
          extractionRunning
            ? (cancelExtraction(), (showMoveHistoryModal = true))
            : (showMoveHistoryModal = true)
        "
      >
        <X v-if="extractionRunning" :size="12" />
        <template v-else>
          <ArrowLeftRight :size="12" />
          <RotateCw :size="10" class="mm-ico-overlap" />
        </template>
      </button>
      <button
        v-if="checked.size > 1"
        class="mm-btn-sm mm-btn-danger"
        :title="$t('mediaManager.deleteBatch')"
        @click="deleteSelected"
      >
        <Trash2 :size="12" />
        {{ checked.size }}
      </button>
      <button class="mm-btn-sm" :title="$t('common.refresh')" @click="loadFiles">
        <RefreshCw :size="12" />
      </button>
      <span
        v-if="newFilesCount > 0"
        class="mm-new-count-inline"
        :title="$t('mediaManager.recentFiles')"
      >
        {{ $t('mediaManager.newFilesShort', { count: newFilesCount }) }}
      </span>
      <button
        v-if="checkedDirs.length > 0 && subPath"
        class="mm-btn-sm mm-btn-accent"
        :title="$t('mediaManager.extractSubfoldersTitle')"
        @click="extractFromSubfolders"
      >
        <ArrowUp />
        {{ $t('mediaManager.extractSubfolders') }}
      </button>
      <button
        v-if="canMoveMulti"
        class="mm-btn-sm mm-btn-accent"
        :title="$t('mediaManager.move')"
        @click="openMoveModalMulti"
      >
        <ArrowLeftRight />
        {{ $t('mediaManager.move') }}
      </button>
    </div>

    <div
      ref="fileListRef"
      class="mm-file-list"
      @scroll="onScroll"
      @mousedown="onLassoStart"
      @mousemove="onLassoMove"
      @mouseup="onLassoEnd"
      @mouseleave="onLassoEnd"
    >
      <div v-if="lasso.active" class="mm-lasso" :style="lassoStyle" />
      <div v-if="loading" class="mm-state">
        <MkSpinner size="sm" />
        <span>{{ $t('mediaManager.loading') }}</span>
      </div>
      <div v-else-if="!filtered.length" class="mm-state">
        <span>{{ $t('mediaManager.noFiles') }}</span>
      </div>
      <template v-else>
        <div v-if="!newNames.length" :style="{ height: vsTop + 'px' }" />
        <div
          v-for="(f, vi) in newNames.length ? filtered : vsItems"
          :key="f.path"
          class="mm-file-row"
          :class="{
            folder: f.type === FILE_TYPE.FOLDER,
            checked: checked.has(newNames.length ? vi : vi + vsStart),
            'mm-has-issue': analysisActive && namingIssues[f.path],
            'mm-drop-target':
              f.type === FILE_TYPE.FOLDER &&
              dragOverFolder === (newNames.length ? vi : vi + vsStart),
          }"
          :draggable="true"
          @click.stop="rowClick($event, newNames.length ? vi : vi + vsStart, f)"
          @contextmenu.prevent="openCtxMenu($event, newNames.length ? vi : vi + vsStart, f)"
          @dragstart="fileDragStart(newNames.length ? vi : vi + vsStart)"
          @dragend="fileDragEnd"
          @dragover.prevent="
            f.type === FILE_TYPE.FOLDER && (dragOverFolder = newNames.length ? vi : vi + vsStart)
          "
          @dragleave="dragOverFolder = null"
          @drop.prevent="
            f.type === FILE_TYPE.FOLDER &&
            (dropOnFolder(newNames.length ? vi : vi + vsStart), (dragOverFolder = null))
          "
          @mouseenter="onFileHover(f, $event)"
          @mouseleave="onFileHoverEnd"
        >
          <div class="mm-check">
            <Check v-if="checked.has(newNames.length ? vi : vi + vsStart)" :stroke-width="3" />
          </div>
          <span class="mm-ficon" :class="{ 'mm-ficon-folder': f.type === FILE_TYPE.FOLDER }">
            <Folder v-if="f.type === FILE_TYPE.FOLDER" :size="14" />
            <Video v-else :size="14" />
          </span>
          <span class="mm-fname" :title="f.name">
            {{
              f.type === FILE_TYPE.FILE && f.name.includes('.')
                ? f.name.slice(0, f.name.lastIndexOf('.'))
                : f.name
            }}
            <span v-if="expandedMode && f.path" class="mm-parent-hint">
              📁 {{ f.path.split('/').slice(-2, -1)[0] }}
            </span>
          </span>
          <span
            v-if="getFileCat(f)"
            class="mm-cat-badge"
            :style="{ background: getFileCat(f).color }"
          >
            {{ getFileCat(f).label }}
          </span>
          <span v-if="isFileNew(f)" class="mm-new-badge">{{ $t('mediaManager.newBadge') }}</span>
          <span v-if="multiCatMode && f._catLabel" class="mm-multicat-badge">
            {{ f._catLabel }}
          </span>
          <span
            v-if="analysisActive && namingIssues[f.path]"
            class="mm-analysis-badge"
            :title="namingIssues[f.path].map(i => i.message).join(', ')"
          >
            {{ namingIssues[f.path].length }}
          </span>
          <span v-if="f.type === FILE_TYPE.FILE && f.name.includes('.')" class="mm-fext">
            {{ f.name.split('.').pop() }}
          </span>
          <span v-if="f.type === FILE_TYPE.FILE" class="mm-fsize">{{ f.size_label }}</span>
          <span
            v-if="f.type === FILE_TYPE.FILE && showQualityScore"
            class="mm-quality-badge"
            :style="{ '--mm-q-color': getQualityColor(computeQualityScore(f.name)) }"
            @mouseenter="showQualityPopup($event, f)"
            @mouseleave="hideQualityPopup"
          >
            {{ computeQualityScore(f.name) }}
          </span>
          <button
            v-if="f.type === FILE_TYPE.FILE"
            class="mm-row-btn mm-row-info"
            :title="''"
            @click.stop="openFileMeta(f)"
          >
            <Info />
          </button>
          <button
            class="mm-row-btn mm-row-move"
            :title="$t('mediaManager.move')"
            @click.stop="openMoveModal(newNames.length ? vi : vi + vsStart)"
          >
            <ArrowLeftRight />
          </button>
          <button
            class="mm-row-btn mm-row-del"
            :title="$t('mediaManager.delete')"
            @click.stop="deleteFile(newNames.length ? vi : vi + vsStart)"
          >
            <X />
          </button>
        </div>
        <div v-if="!newNames.length" :style="{ height: vsBottom + 'px' }" />
      </template>
    </div>

    <div
      v-if="hoverThumbnail.visible && hoverThumbnail.url"
      class="mm-thumb-hover"
      :style="{ left: hoverThumbnail.x + 'px', top: hoverThumbnail.y + 'px' }"
    >
      <img :src="hoverThumbnail.url" />
    </div>

    <Teleport to="body">
      <div
        v-if="qualityPopup.visible"
        class="mm-quality-popup"
        :style="{ left: qualityPopup.x + 'px', top: qualityPopup.y + 'px' }"
      >
        <div class="mm-qp-header">
          <span class="mm-qp-score" :style="{ color: getQualityColor(qualityPopup.score) }">
            {{ qualityPopup.score }}/100
          </span>
        </div>
        <div v-if="qualityPopup.penalties.length" class="mm-qp-penalties">
          <div v-for="(p, i) in qualityPopup.penalties" :key="i" class="mm-qp-penalty">
            <span class="mm-qp-penalty-points">-{{ p.points }}</span>
            {{ p.label }}
          </div>
        </div>
        <div v-else class="mm-qp-perfect">{{ $t('mediaManager.qualityPerfect') }}</div>
        <hr class="mm-qp-sep" />
        <div class="mm-qp-example-label">{{ $t('mediaManager.qualityExample100') }}</div>
        <div class="mm-qp-example-code">Avatar (2024) 1080p x265 DTS.mkv</div>
      </div>
    </Teleport>

    <Teleport to="body">
      <div
        v-if="ctxMenu.show"
        class="mm-ctx-menu"
        :style="{ top: ctxMenu.y + 'px', left: ctxMenu.x + 'px' }"
      >
        <button class="mm-ctx-item" @click="ctxRename">
          <Pencil :size="13" />
          {{ $t('mediaManager.ctxRename') }}
        </button>
        <button class="mm-ctx-item" @click="ctxMove">
          <ArrowLeftRight :size="13" />
          {{ $t('mediaManager.ctxMove') }}
        </button>
        <button v-if="ctxMenu.file?.type === FILE_TYPE.FILE" class="mm-ctx-item" @click="ctxInfo">
          <Info :size="13" />
          {{ $t('mediaManager.ctxInfo') }}
        </button>
        <div class="mm-ctx-sep" />
        <button class="mm-ctx-item mm-ctx-danger" @click="ctxDelete">
          <Trash2 :size="13" />
          {{ $t('mediaManager.ctxDelete') }}
        </button>
      </div>
      <div v-if="inlineRename.show" class="mm-overlay show" @click.self="inlineRename.show = false">
        <div class="mm-ctx-rename-modal">
          <div class="mm-cat-modal-header">
            <span>{{ $t('mediaManager.ctxRename') }}</span>
            <button class="mm-btn-sm mm-close-btn" @click="inlineRename.show = false">
              <X :size="12" />
            </button>
          </div>
          <div class="mm-inline-rename-body">
            <input
              ref="renameInputRef"
              v-model="inlineRename.value"
              class="mm-cat-input mm-input-full"
              @keydown.enter="submitInlineRename"
            />
          </div>
          <div class="mm-cat-modal-footer">
            <button class="mm-btn-sm" @click="inlineRename.show = false">
              {{ $t('common.cancel') }}
            </button>
            <button
              class="mm-btn-sm mm-btn-accent"
              :disabled="!inlineRename.value.trim()"
              @click="submitInlineRename"
            >
              <Check :size="12" />
              {{ $t('mediaManager.ctxRename') }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, inject } from 'vue'
import { useMediaManager, CATS } from '@/composables/useMediaManager'
import { useMMFileListUI } from '@/composables/useMMFileListUI'
import {
  ArrowDownAZ,
  ArrowDownUp,
  ArrowLeftRight,
  ArrowUp,
  Check,
  CircleCheck,
  Folder,
  Info,
  Pencil,
  RefreshCw,
  RotateCw,
  Star,
  Trash2,
  Video,
  X,
} from 'lucide-vue-next'
import { FILE_TYPE } from '@/constants/mediaManager'
import MkSpinner from '@/components/common/MkSpinner.vue'

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
  lasso,
  lassoStyle,
  onLassoStart,
  onLassoMove,
  onLassoEnd,
  hoverThumbnail,
  onFileHover,
  onFileHoverEnd,
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
</script>
<style scoped>
.mm-header-actions {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  flex-shrink: 0;
}
.mm-ico-11 {
  width: 11px;
  height: 11px;
}
.mm-ico-12 {
  width: 12px;
  height: 12px;
}
.mm-ico-overlap {
  margin-left: -4px;
}
.mm-qp-penalty-points {
  color: var(--color-error);
}
.mm-qp-perfect {
  font-size: var(--text-2xs);
  color: var(--mm-green);
}
.mm-qp-sep {
  border-color: var(--border);
  margin: 0.4rem 0;
}
.mm-qp-example-label {
  font-size: var(--text-3xs);
  color: var(--text-muted);
}
.mm-qp-example-code {
  font-family: monospace;
  font-size: 0.63rem;
  color: var(--accent-400);
  margin-top: 0.2rem;
  word-break: break-all;
}
.mm-close-btn {
  padding: 3px 8px;
}
.mm-inline-rename-body {
  padding: 0.8rem 1rem;
}
.mm-input-full {
  width: 100%;
}
</style>
