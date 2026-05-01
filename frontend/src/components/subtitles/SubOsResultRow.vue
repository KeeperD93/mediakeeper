<template>
  <div class="sub-os-row">
    <input v-if="selectable" type="checkbox" class="sub-os-check" :checked="selected" @change="$emit('select', result)" />
    <span class="sub-os-lang" :class="'lang-' + result.language">{{ result.language.toUpperCase() }}</span>
    <div class="sub-os-info">
      <span class="sub-os-name">{{ result.file_name }}</span>
      <span class="sub-os-meta">
        <SubQualityStars v-if="result.quality_score" :score="result.quality_score" :result="result" />
        <span v-if="result.hash_match" class="sub-tag tag-hash">HASH</span>
        <span v-if="result.hearing_impaired" class="sub-tag tag-hi">HI</span>
        <span v-if="result.foreign_parts_only" class="sub-tag tag-forced">{{ $t('subtitles.forced') }}</span>
        <span v-else class="sub-tag tag-full">{{ $t('subtitles.full') }}</span>
        <span v-if="result.from_trusted" class="sub-tag tag-trusted">{{ $t('subtitles.trusted') }}</span>
        <span v-if="result.ai_translated" class="sub-tag tag-ai">AI</span>
        <span v-if="result.machine_translated" class="sub-tag tag-machine">MT</span>
        <span class="sub-os-dl-count">{{ result.download_count.toLocaleString() }}</span>
        <span v-if="result.ratings" class="sub-os-rating" :title="$t('subtitles.communityRating')">{{ result.ratings }}/10</span>
      </span>
    </div>
    <button class="sub-os-dl-btn" :disabled="downloading" @click="$emit('download', result)">
      <span v-if="downloading" class="mk-spin mk-spin-12" />
      <Download v-else :size="14" />
    </button>
  </div>
</template>

<script setup>
import SubQualityStars from './SubQualityStars.vue'
import { Download } from 'lucide-vue-next'

defineProps({
  result: { type: Object, required: true },
  downloading: { type: Boolean, default: false },
  selectable: { type: Boolean, default: false },
  selected: { type: Boolean, default: false },
})
defineEmits(['download', 'select'])
</script>

<style scoped>
.sub-os-check { accent-color: var(--accent-500); cursor: pointer; flex-shrink: 0; }
.sub-os-row { display: flex; align-items: center; gap: 10px; padding: 8px 0; border-bottom: .5px solid var(--border-subtle); }
.sub-os-row:last-child { border-bottom: none; }
.sub-os-lang { font-size: var(--text-3xs); font-weight: var(--font-bold); padding: 3px 7px; border-radius: 5px; flex-shrink: 0; background: rgba(var(--accent-rgb),.12); color: var(--accent-400); }
.lang-fr { background: rgba(59,130,246,.12); color: var(--color-info); }
.lang-en { background: rgba(var(--color-success-rgb),.12); color: var(--color-success); }
.sub-os-info { flex: 1; min-width: 0; }
.sub-os-name { display: block; font-size: var(--text-xs); color: var(--text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.sub-os-meta { display: flex; align-items: center; gap: 5px; flex-wrap: wrap; margin-top: 2px; }
.sub-tag { font-size: .54rem; padding: 1px 5px; border-radius: 3px; font-weight: var(--font-medium); }
.tag-hi { background: rgba(var(--color-warning-rgb),.12); color: var(--color-warning); }
.tag-forced { background: rgba(168,85,247,.12); color: #a855f7; }
.tag-full { background: rgba(var(--color-success-rgb),.08); color: rgba(var(--color-success-rgb),.5); }
.tag-trusted { background: rgba(var(--color-success-rgb),.12); color: var(--color-success); }
.tag-ai { background: rgba(var(--color-info-rgb),.12); color: var(--color-info); }
.tag-machine { background: rgba(244,63,94,.12); color: #fb7185; }
.tag-hash { background: rgba(52,211,153,.12); color: #34d399; }
.sub-os-dl-count { font-size: .58rem; color: var(--text-muted); }
.sub-os-dl-count::before { content: '\2193 '; }
.sub-os-rating { font-size: .58rem; color: var(--color-warning); }
.sub-os-rating::before { content: '\2605 '; }
.sub-os-dl-btn {
  width: 30px; height: 30px; border-radius: var(--radius-btn); display: flex; align-items: center; justify-content: center;
  background: rgba(var(--accent-rgb),.08); color: var(--accent-400);
  border: .5px solid rgba(var(--accent-rgb),.15); cursor: pointer; flex-shrink: 0;
}
.sub-os-dl-btn:hover:not(:disabled) { background: rgba(var(--accent-rgb),.18); }
.sub-os-dl-btn:disabled { opacity: .4; cursor: default; }
</style>
