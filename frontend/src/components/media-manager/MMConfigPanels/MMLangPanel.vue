<template>
  <div class="mm-config-body">
    <p class="mm-desc">{{ $t('mediaManager.langDesc') }}</p>
    <div class="mm-label">{{ $t('mediaManager.renameLanguage') }}</div>
    <div class="mm-lang-stack">
      <label v-for="lang in TMDB_LANGS" :key="lang.code" class="mm-rule-row mm-clickable">
        <input
          :value="lang.code"
          :checked="tmdbLangDraft === lang.code"
          type="radio"
          class="mm-chkbox mm-radio-accent"
          @change="$emit('update:tmdbLangDraft', lang.code)"
        />
        <div class="mm-rule-text">
          <div class="mm-rule-label">{{ lang.flag }} {{ lang.label }}</div>
          <div class="mm-rule-hint">{{ lang.hint }}</div>
        </div>
        <div class="mm-lang-tags">
          <span v-for="tag in lang.tags" :key="tag" class="mm-lang-tag">{{ tag }}</span>
        </div>
      </label>
    </div>
    <div class="mm-config-footer">
      <button
        class="mm-btn-sm mm-btn-success"
        :class="{ 'mm-btn-saved': saved }"
        @click="$emit('save')"
      >
        <Check />
        {{ saved ? $t('common.saved') + ' ✓' : $t('common.save') }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { Check } from 'lucide-vue-next'
import { TMDB_LANGS } from './tmdbLangs'

defineProps({
  tmdbLangDraft: { type: String, required: true },
  saved: { type: Boolean, default: false },
})
defineEmits(['save', 'update:tmdbLangDraft'])
</script>

<style scoped>
.mm-desc {
  font-size: var(--text-xs);
  color: var(--text-muted);
  margin-bottom: 0.75rem;
}
.mm-clickable {
  cursor: pointer;
}
.mm-lang-stack {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  margin-top: 0.4rem;
}
.mm-radio-accent {
  accent-color: var(--accent-500);
}
.mm-lang-tags {
  display: flex;
  gap: 0.25rem;
  flex-wrap: wrap;
  justify-content: flex-end;
  max-width: 160px;
}
</style>
