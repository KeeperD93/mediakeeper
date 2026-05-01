<template>
  <div class="mm-config-body">
    <p class="mm-desc">{{ $t('mediaManager.crossCatDesc') }}</p>
    <button class="mm-btn-sm mm-btn-accent" :disabled="!newNames.length || checkingDuplicates" @click="checkCrossCatDuplicates">
      <MkSpinner v-if="checkingDuplicates" size="sm" inline />
      <Search v-else :size="12" />
      {{ checkingDuplicates ? $t('mediaManager.analyzingDupes') : $t('mediaManager.checkDupes') }}
    </button>
    <div v-if="crossCatDuplicates.length" class="mm-dupes-list">
      <div class="mm-label mm-label-error">{{ crossCatDuplicates.length }} {{ $t('mediaManager.dupesDetected') }}</div>
      <div v-for="d in crossCatDuplicates" :key="d.path" class="mm-conflict-row">
        <span class="mm-conflict-name">{{ d.name }}</span>
        <span class="mm-conflict-size">{{ d.cat }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useMediaManager } from '@/composables/useMediaManager'
import { Search } from 'lucide-vue-next'
import MkSpinner from '@/components/common/MkSpinner.vue'

const { newNames, crossCatDuplicates, checkingDuplicates, checkCrossCatDuplicates } = useMediaManager()
</script>

<style scoped>
/* Section description */
.mm-desc { font-size: var(--text-xs); color: var(--text-muted); margin-bottom: .75rem; }
/* Results list container (appears after the "check" button) */
.mm-dupes-list { margin-top: .75rem; }
/* Label tinted red to signal duplicates detected */
.mm-label-error { color: var(--color-error); margin-bottom: .4rem; }
</style>
