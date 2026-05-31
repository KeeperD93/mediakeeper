<template>
  <div class="mm-config-body">
    <div class="mm-rf-syntax">{{ $t('mediaManager.formatSyntaxHint') }}</div>
    <div class="mm-section mm-section-lg">
      <div class="mm-label">{{ $t('mediaManager.formatMovies') }}</div>
      <input
        v-model="renameFormatDraft.movie"
        class="mm-folder-input mm-input-mono"
        placeholder="{t} ({y})"
      />
      <div class="mm-rf-preview">
        {{ $t('mediaManager.formatPreview') }}
        <span class="mm-rf-ex">{{ previewMovie }}</span>
      </div>
    </div>
    <div class="mm-section">
      <div class="mm-label">{{ $t('mediaManager.formatSeries') }}</div>
      <input
        v-model="renameFormatDraft.tv"
        class="mm-folder-input mm-input-mono"
        placeholder="{n} - {s00e00} - {t}"
      />
      <div class="mm-rf-preview">
        {{ $t('mediaManager.formatPreview') }}
        <span class="mm-rf-ex">{{ previewTv }}</span>
      </div>
    </div>
    <div class="mm-section mm-section-lg">
      <div class="mm-label mm-label-gap">{{ $t('mediaManager.formatExamples') }}</div>
      <div class="mm-rf-examples">
        <div
          v-for="ex in RF_EXAMPLES"
          :key="ex.f"
          class="mm-rf-ex-row mm-clickable"
          :title="$t('mediaManager.clickToUse')"
          @click="renameFormatDraft.tv = ex.f"
        >
          <code class="mm-rf-code">{{ ex.f }}</code>
          <span class="mm-rf-arrow">→</span>
          <span class="mm-rf-result">{{ ex.r }}</span>
        </div>
      </div>
    </div>
    <div class="mm-config-footer">
      <button
        class="mm-btn-sm mm-btn-success"
        :class="{ 'mm-btn-saved': saved }"
        @click="$emit('save')"
      >
        <Check />
        {{ saved ? $t('mediaManager.savedBtnLabel') : $t('mediaManager.saveBtnLabel') }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { Check } from 'lucide-vue-next'

const RF_EXAMPLES = [
  { f: '{n} - {s00e00} - {t}', r: 'SeriesName - S01E01 - EpisodeName' },
  { f: '{n} - {sxe} - {t} {subt}', r: 'SeriesName - 1x01 - EpisodeName VOSTFR' },
  { f: '{t} ({y})', r: 'MovieName (2005)' },
  { f: '{n} [{airdate}] {t}', r: 'SeriesName [2002-12-20] EpisodeName' },
]

const renameFormatDraft = defineModel('renameFormatDraft', { type: Object, required: true })
defineProps({
  previewMovie: { type: String, required: true },
  previewTv: { type: String, required: true },
  saved: { type: Boolean, default: false },
})
defineEmits(['save'])
</script>

<style scoped>
.mm-section {
  margin-top: 0.8rem;
}
.mm-section-lg {
  margin-top: 0.9rem;
}
.mm-label-gap {
  margin-bottom: 0.4rem;
}
.mm-input-mono {
  font-family: monospace;
}
.mm-clickable {
  cursor: pointer;
}
</style>
