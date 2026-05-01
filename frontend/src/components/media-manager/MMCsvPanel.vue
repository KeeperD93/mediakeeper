<template>
  <div class="mm-config-body">
    <p class="mm-desc">{{ $t('mediaManager.exportDesc') }}</p>
    <div class="mm-label">{{ $t('mediaManager.exportLabel') }}</div>
    <div class="mm-action-row mm-action-row-top">
      <button class="mm-btn-sm mm-btn-accent" :disabled="!newNames.length" @click="exportRenameCsv(newNames)">
        <Download :size="12" />
        <span v-if="useCountSuffix">{{ $t('mediaManager.exportCsvCount', { count: newNames.length }) }}</span>
        <span v-else>{{ $t('mediaManager.exportLabel') }} ({{ newNames.length }})</span>
      </button>
    </div>
    <div class="mm-action-row">
      <button class="mm-btn-sm" @click="downloadCsvTemplate">
        <Download :size="12" />
        {{ $t('mediaManager.downloadTemplate') }}
      </button>
    </div>
    <div class="mm-label">{{ $t('mediaManager.importLabel') }}</div>
    <p class="mm-hint">{{ $t('mediaManager.expectedColumns') }}</p>
    <label class="mm-csv-drop" :class="{active: csvDragOver}" @dragover.prevent="csvDragOver=true" @dragleave="csvDragOver=false" @drop.prevent="dropCsv($event)">
      <Upload :size="22" :stroke-width="1.5" />
      <span>{{ $t('mediaManager.dragCsv') }}</span>
      <input type="file" accept=".csv" class="mm-file-hidden" @change="pickCsvFile($event)"/>
    </label>
    <div v-if="csvPreview.length" class="mm-preview-block">
      <div class="mm-label">{{ $t('mediaManager.previewLines', { n: csvPreview.length }) }}</div>
      <div class="mm-preview-scroll">
        <div v-for="(row,ri) in csvPreview.slice(0,8)" :key="ri" class="mm-hist-item mm-preview-row">
          <span class="mm-preview-old">{{ row.oldName }}</span>
          <span class="mm-preview-new">→ {{ row.newName }}</span>
        </div>
      </div>
      <button class="mm-btn-sm mm-btn-success mm-apply-btn" @click="applyCsvImport">
        <Check />
        {{ $t('mediaManager.loadToRight') }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { useMediaManager } from '@/composables/useMediaManager'
import { useMMConfigPanels } from '@/composables/useMMConfigPanels'
import { Check, Download, Upload } from 'lucide-vue-next'

// `useCountSuffix` picks the i18n key used for the export button label:
// Advanced modal uses the count-suffix variant ("Export CSV (3 lines)"),
// Config modal uses the plain variant. Both paths keep the same button
// otherwise.
defineProps({ useCountSuffix: { type: Boolean, default: false } })

const { newNames, exportRenameCsv } = useMediaManager()
const { csvDragOver, csvPreview, dropCsv, pickCsvFile, applyCsvImport, downloadCsvTemplate } = useMMConfigPanels()
</script>

<style scoped>
/* Section description */
.mm-desc { font-size: var(--text-xs); color: var(--text-muted); margin-bottom: .75rem; }
/* Secondary hint under a label */
.mm-hint { font-size: var(--text-2xs); color: var(--text-muted); margin: .3rem 0 .5rem; }
/* Action row: single-line button row */
.mm-action-row { display: flex; gap: .4rem; margin-bottom: .8rem; }
/* First action row keeps a small top margin after the preceding label */
.mm-action-row-top { margin-top: .4rem; }
/* Hides the native file input inside the drop zone */
.mm-file-hidden { display: none; }
/* Preview block (lines from parsed CSV) */
.mm-preview-block { margin-top: .6rem; }
.mm-preview-scroll { max-height: 140px; overflow-y: auto; margin-top: .3rem; }
.mm-preview-row { flex-direction: row; gap: .4rem; }
.mm-preview-old { color: var(--text-muted); flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.mm-preview-new { color: var(--mm-green); flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
/* Apply-import button */
.mm-apply-btn { margin-top: .5rem; }
</style>
