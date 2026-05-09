<template>
  <div class="mm-toolbar">
    <label class="mm-chk-all-label" :title="$t('mediaManager.toggleAll')">
      <input
        type="checkbox"
        :checked="checked.size > 0 && checked.size === filtered.length"
        :indeterminate.prop="checked.size > 0 && checked.size < filtered.length"
        class="mm-chkbox"
        @change="e => $emit('toggle-all', e.target.checked)"
      />
    </label>
    <input
      :value="filterQuery"
      :placeholder="$t('mediaManager.filterPlaceholder')"
      class="mm-filter"
      @input="e => $emit('update:filterQuery', e.target.value)"
    />
    <div class="mm-sort-group" :title="$t('mediaManager.sortAlpha')">
      <button
        class="mm-btn-sm mm-sort-btn"
        :class="{ 'mm-btn-accent': sortMode.startsWith('name') }"
        @click="$emit('cycle-sort-name')"
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
        @click="$emit('cycle-sort-size')"
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
      @click="$emit('update:showQualityScore', !showQualityScore)"
    >
      <Star class="mm-ico-12" />
    </button>
    <button
      class="mm-btn-sm"
      :class="{ 'mm-btn-warn': analysisActive && issuesCount > 0 }"
      :title="$t('mediaManager.configuration')"
      @click="analysisActive ? $emit('clear-analysis') : $emit('analyze-names')"
    >
      <CircleCheck :size="12" />
      <span v-if="analysisActive && issuesCount > 0" class="mm-issue-count">
        {{ issuesCount }}
      </span>
    </button>
    <button
      class="mm-btn-sm"
      :title="$t('mediaManager.renameHistoryTitle')"
      @click="$emit('show-history')"
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
      @click="$emit('show-move-history')"
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
      @click="$emit('delete-selected')"
    >
      <Trash2 :size="12" />
      {{ checked.size }}
    </button>
    <button class="mm-btn-sm" :title="$t('common.refresh')" @click="$emit('load-files')">
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
      @click="$emit('extract-subfolders')"
    >
      <ArrowUp />
      {{ $t('mediaManager.extractSubfolders') }}
    </button>
    <button
      v-if="canMoveMulti"
      class="mm-btn-sm mm-btn-accent"
      :title="$t('mediaManager.move')"
      @click="$emit('open-move-multi')"
    >
      <ArrowLeftRight />
      {{ $t('mediaManager.move') }}
    </button>
  </div>
</template>

<script setup>
import {
  ArrowDownAZ,
  ArrowDownUp,
  ArrowLeftRight,
  ArrowUp,
  CircleCheck,
  Pencil,
  RefreshCw,
  RotateCw,
  Star,
  Trash2,
  X,
} from 'lucide-vue-next'

defineProps({
  filterQuery: { type: String, required: true },
  sortMode: { type: String, required: true },
  showQualityScore: { type: Boolean, required: true },
  analysisActive: { type: Boolean, required: true },
  issuesCount: { type: Number, required: true },
  extractionRunning: { type: Boolean, required: true },
  checked: { type: Set, required: true },
  filtered: { type: Array, required: true },
  newFilesCount: { type: Number, required: true },
  checkedDirs: { type: Array, required: true },
  subPath: { type: String, default: '' },
  canMoveMulti: { type: Boolean, required: true },
})
defineEmits([
  'update:filterQuery',
  'update:showQualityScore',
  'toggle-all',
  'cycle-sort-name',
  'cycle-sort-size',
  'analyze-names',
  'clear-analysis',
  'show-history',
  'show-move-history',
  'delete-selected',
  'load-files',
  'extract-subfolders',
  'open-move-multi',
])
</script>

<style scoped>
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
</style>
