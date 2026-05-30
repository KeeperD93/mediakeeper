<template>
  <div
    class="mm-file-row"
    :class="{
      folder: f.type === FILE_TYPE.FOLDER,
      checked: isChecked,
      'mm-has-issue': analysisActive && namingIssues[f.path],
      'mm-drop-target': f.type === FILE_TYPE.FOLDER && isDropTarget,
    }"
    :draggable="true"
    @click.stop="$emit('row-click', $event)"
    @contextmenu.prevent="$emit('row-ctx', $event)"
    @dragstart="$emit('drag-start')"
    @dragend="$emit('drag-end')"
    @dragover.prevent="f.type === FILE_TYPE.FOLDER && $emit('drag-over')"
    @dragleave="$emit('drag-leave')"
    @drop.prevent="f.type === FILE_TYPE.FOLDER && $emit('drop')"
  >
    <div class="mm-check">
      <Check v-if="isChecked" :stroke-width="3" />
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
    <span v-if="getFileCat(f)" class="mm-cat-badge" :style="{ background: getFileCat(f).color }">
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
      @mouseenter="$emit('quality-enter', $event)"
      @mouseleave="$emit('quality-leave')"
    >
      {{ computeQualityScore(f.name) }}
    </span>
    <button
      v-if="f.type === FILE_TYPE.FILE"
      class="mm-row-btn mm-row-info"
      :title="''"
      @click.stop="$emit('open-meta')"
    >
      <Info />
    </button>
    <button
      class="mm-row-btn mm-row-move"
      :title="$t('mediaManager.move')"
      @click.stop="$emit('open-move')"
    >
      <ArrowLeftRight />
    </button>
    <button
      class="mm-row-btn mm-row-del"
      :title="$t('mediaManager.delete')"
      @click.stop="$emit('delete-file')"
    >
      <X />
    </button>
  </div>
</template>

<script setup>
import { ArrowLeftRight, Check, Folder, Info, Video, X } from 'lucide-vue-next'
import { FILE_TYPE } from '@/constants/mediaManager'

defineProps({
  f: { type: Object, required: true },
  isChecked: { type: Boolean, required: true },
  isDropTarget: { type: Boolean, default: false },
  expandedMode: { type: Boolean, default: false },
  multiCatMode: { type: Boolean, default: false },
  analysisActive: { type: Boolean, default: false },
  namingIssues: { type: Object, default: () => ({}) },
  showQualityScore: { type: Boolean, default: false },
  getFileCat: { type: Function, required: true },
  isFileNew: { type: Function, required: true },
  computeQualityScore: { type: Function, required: true },
  getQualityColor: { type: Function, required: true },
})
defineEmits([
  'row-click',
  'row-ctx',
  'drag-start',
  'drag-end',
  'drag-over',
  'drag-leave',
  'drop',
  'quality-enter',
  'quality-leave',
  'open-meta',
  'open-move',
  'delete-file',
])
</script>
