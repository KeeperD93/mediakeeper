<template>
  <div class="mm-col">
    <div class="mm-col-header">
      <span class="mm-col-title">{{ $t('mediaManager.newNames') }}</span>
      <span class="mm-count">{{ newNames.length || '—' }}</span>
    </div>
    <div class="mm-toolbar mm-toolbar--between">
      <span class="mm-hint">{{ $t('mediaManager.dragToReorder') }}</span>
      <div class="mm-row-flex-tight">
        <button v-if="selectedNew.size > 0" class="mm-btn-sm mm-btn-danger" @click="deleteSelected">
          <Trash2 :size="11" />
          {{ $t('mediaManager.deleteSelected', { n: selectedNew.size }) }}
        </button>
        <button
          class="mm-btn-sm"
          :class="{ 'mm-btn-accent': diffMode }"
          :title="$t('mediaManager.compareMode')"
          @click="diffMode = !diffMode"
        >
          <ArrowLeftRight :size="11" />
          {{ $t('mediaManager.diff') }}
        </button>
        <button class="mm-btn-sm" @click="clearRight">
          <X />
          {{ $t('mediaManager.clear') }}
        </button>
      </div>
    </div>
    <div
      ref="rightListRef"
      class="mm-file-list"
      tabindex="0"
      @scroll="onScroll"
      @keydown.delete.prevent="deleteSelected"
      @keydown.backspace.prevent="deleteSelected"
      @keydown.esc.prevent="clearSelection"
    >
      <div v-if="lassoDragging" class="mm-lasso" :style="lassoStyle" />
      <div v-if="!newNames.length" class="mm-state">
        <ChevronRight :size="24" />
        <span>{{ $t('mediaManager.waitingGeneration') }}</span>
      </div>
      <template v-for="(n, i) in newNames" :key="i">
        <div
          class="mm-new-row"
          :class="{
            warn: liveEpCheck[i]?.epMismatch || n.mismatch,
            'warn-strong': liveEpCheck[i]?.seasonMismatch || n.mismatchStrong,
            'drag-over-r': dragOverRight === i,
            selected: selectedNew.has(i),
          }"
          draggable="true"
          @dragstart="dStart(i)"
          @dragover.prevent="dragOverRight = i"
          @dragleave="dragOverRight = null"
          @drop.prevent="(dDrop(i), (dragOverRight = null))"
          @contextmenu.prevent="openRenameCtx($event, i)"
        >
          <span class="mm-drag-handle">⠿</span>
          <span
            v-if="fileRenameStatus[n.path]"
            class="mm-rename-status"
            :class="'st-' + fileRenameStatus[n.path]"
          >
            <MkSpinner v-if="fileRenameStatus[n.path] === 'renaming'" size="sm" inline />
            <Check v-else-if="fileRenameStatus[n.path] === 'done'" :size="10" :stroke-width="3" />
            <X v-else-if="fileRenameStatus[n.path] === 'error'" :size="10" :stroke-width="3" />
          </span>
          <span class="mm-new-idx">{{ String(i + 1).padStart(2, '0') }}</span>
          <span class="mm-new-name" :title="n.name">
            {{ n.ext ? n.name.slice(0, -(n.ext.length + 1)) : n.name }}
          </span>
          <span v-if="n.ext" class="mm-fext">{{ n.ext }}</span>
          <span v-if="n.category" class="mm-cat-badge" :style="{ background: n.category.color }">
            {{ n.category.label }}
          </span>
          <span
            v-if="liveEpCheck[i]?.seasonMismatch"
            class="mm-warn-badge mm-warn-ep"
            :title="
              $t('mediaManager.seasonMismatchTitle', {
                src: String(liveEpCheck[i].srcSeason).padStart(2, '0'),
                prop: String(liveEpCheck[i].propSeason).padStart(2, '0'),
              })
            "
          >
            ⚠ S{{ String(liveEpCheck[i].srcSeason).padStart(2, '0') }}≠S{{
              String(liveEpCheck[i].propSeason).padStart(2, '0')
            }}
          </span>
          <span
            v-else-if="liveEpCheck[i]?.epMismatch"
            class="mm-warn-badge mm-warn-ep"
            :title="
              $t('mediaManager.epMismatchTitle', {
                src: String(liveEpCheck[i].srcEp).padStart(2, '0'),
                prop: String(liveEpCheck[i].propEp).padStart(2, '0'),
              })
            "
          >
            ⚠ E{{ String(liveEpCheck[i].srcEp).padStart(2, '0') }}→E{{
              String(liveEpCheck[i].propEp).padStart(2, '0')
            }}
          </span>
          <span
            v-else-if="n.mismatch"
            class="mm-warn-badge"
            :title="$t('mediaManager.uncertainMatch')"
          >
            ?
          </span>
          <button
            class="mm-del-btn mm-copy-btn"
            :title="$t('mediaManager.copyName')"
            @click="copyName(n.name)"
          >
            <Copy />
          </button>
          <button class="mm-del-btn" @click="removeRight(i)">
            <X />
          </button>
        </div>
        <div v-if="diffMode && n.oldName" class="mm-diff-row">
          <div class="mm-diff-old">
            <span class="mm-diff-label">{{ $t('mediaManager.diffBefore') }}</span>
            <span class="mm-diff-text">{{ n.oldName }}</span>
          </div>
          <div class="mm-diff-new">
            <span class="mm-diff-label">{{ $t('mediaManager.diffAfter') }}</span>
            <template v-for="(chunk, ci) in computeDiff(n.oldName, n.name)" :key="ci">
              <span
                :class="
                  chunk.type === DIFF_TYPE.ADD
                    ? 'mm-diff-add'
                    : chunk.type === DIFF_TYPE.DEL
                      ? 'mm-diff-del'
                      : ''
                "
              >
                {{ chunk.text }}
              </span>
            </template>
          </div>
        </div>
      </template>
    </div>
    <!-- Menu contextuel nom generated -->
    <Teleport to="body">
      <div
        v-if="renameCtx.show"
        class="mm-ctx-menu"
        :style="{ top: renameCtx.y + 'px', left: renameCtx.x + 'px' }"
      >
        <button class="mm-ctx-item mm-ctx-danger" @click="renameCtxDelete">
          <Trash2 :size="13" />
          {{ $t('mediaManager.ctxDelete') }}
        </button>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useMediaManager } from '@/composables/useMediaManager'
import { rootZoom } from '@/utils/zoom'
import { useMMRenamePanelUI } from '@/composables/useMMRenamePanelUI'
import { useToast } from '@/composables/useToast'
import { TOAST_TYPE } from '@/constants/toast'
import { ArrowLeftRight, Check, ChevronRight, Copy, Trash2, X } from 'lucide-vue-next'
import { DIFF_TYPE, FILE_TYPE } from '@/constants/mediaManager'
import MkSpinner from '@/components/common/MkSpinner.vue'

const { t } = useI18n()
const { showToast } = useToast()

const {
  newNames,
  fileRenameStatus,
  filtered,
  dStart,
  dDrop,
  removeRight,
  clearRight,
  computeDiff,
} = useMediaManager()

async function copyName(name) {
  try {
    await navigator.clipboard.writeText(name)
    showToast(t('mediaManager.nameCopied'), TOAST_TYPE.OK)
  } catch {
    showToast(t('common.copyFailed'), TOAST_TYPE.ERR)
  }
}

const diffMode = ref(false)
const dragOverRight = ref(null)
const rightListRef = ref(null)

const {
  lassoDragging,
  lassoStyle,
  selectedNew,
  deleteSelected: _deleteSelected,
  clearSelection,
} = useMMRenamePanelUI({ rightListRef, newNames })

function deleteSelected() {
  _deleteSelected(removeRight)
}

// ── Menu contextuel ──
const renameCtx = ref({ show: false, x: 0, y: 0, idx: null })
let _renameCtxClose = null

function openRenameCtx(e, i) {
  if (_renameCtxClose) {
    document.removeEventListener('mousedown', _renameCtxClose)
    _renameCtxClose = null
  }
  const z = rootZoom() // admin zoom: divide the final position (utils/zoom)
  renameCtx.value = { show: true, x: e.clientX / z, y: e.clientY / z, idx: i }
  _renameCtxClose = ev => {
    if (!ev.target.closest('.mm-ctx-menu')) {
      renameCtx.value.show = false
      document.removeEventListener('mousedown', _renameCtxClose)
      _renameCtxClose = null
    }
  }
  setTimeout(() => document.addEventListener('mousedown', _renameCtxClose), 0)
}

function renameCtxDelete() {
  removeRight(renameCtx.value.idx)
  renameCtx.value.show = false
}

const emit = defineEmits(['scroll'])

let _scrollRaf = null
function onScroll(e) {
  if (_scrollRaf) return
  _scrollRaf = requestAnimationFrame(() => {
    emit('scroll', e.target.scrollTop)
    _scrollRaf = null
  })
}

defineExpose({ rightListRef })

// Live episode coherence check
function _extractEpNum(name) {
  if (!name) return null
  const mSE = name.match(/[Ss]\d{1,2}[Ee](\d{1,2})/)
  if (mSE) return parseInt(mSE[1])
  const mXx = name.match(/\d{1,2}x(\d{2})/)
  if (mXx) return parseInt(mXx[1])
  return null
}
function _extractSeasonNum(name) {
  if (!name) return null
  const m = name.match(/[Ss](\d{1,2})[Ee]\d{1,2}/)
  return m ? parseInt(m[1]) : null
}
const liveEpCheck = computed(() => {
  return newNames.value.map((n, i) => {
    const srcFile = filtered.value[i]
    if (!srcFile || srcFile.type !== FILE_TYPE.FILE) return null
    const srcEp = _extractEpNum(srcFile.name)
    const propEp = _extractEpNum(n.name)
    const srcSeason = _extractSeasonNum(srcFile.name)
    const propSeason = _extractSeasonNum(n.name)
    if (srcEp === null || propEp === null) return null
    return {
      epMismatch: srcEp !== propEp,
      seasonMismatch: srcSeason !== null && propSeason !== null && srcSeason !== propSeason,
      srcEp,
      propEp,
      srcSeason,
      propSeason,
    }
  })
})
</script>

<style scoped>
.mm-new-row.selected {
  background: rgb(var(--accent-rgb), 0.12);
  outline: 1px solid var(--accent-500);
  outline-offset: -1px;
}
.mm-file-list:focus {
  outline: none;
}
</style>
