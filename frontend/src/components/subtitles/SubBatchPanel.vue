<template>
  <div v-if="selectedItems.length" class="sub-batch glass-card">
    <div class="sub-batch-info">
      <span class="sub-batch-count">
        {{ selectedItems.length }} {{ $t('subtitles.itemsSelected') }}
      </span>
      <button class="sub-batch-clear" @click="$emit('clear')">
        <X :size="12" />
      </button>
    </div>
    <button class="sub-batch-go" :disabled="batchRunning" @click="$emit('start')">
      <Download :size="14" />
      {{ $t('subtitles.downloadBest') }}
    </button>
  </div>

  <!-- Progress -->
  <SubBatchProgress v-if="batchRunning" @cancel="$emit('cancel')" />
</template>

<script setup>
import SubBatchProgress from './SubBatchProgress.vue'
import { Download, X } from 'lucide-vue-next'

defineProps({
  selectedItems: { type: Array, default: () => [] },
  batchRunning: { type: Boolean, default: false },
})
defineEmits(['start', 'clear', 'cancel'])
</script>

<style scoped>
.sub-batch {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  margin-bottom: 8px;
}
.sub-batch-info {
  display: flex;
  align-items: center;
  gap: 8px;
}
.sub-batch-count {
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  color: var(--text-primary);
}
.sub-batch-clear {
  width: 22px;
  height: 22px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
}
.sub-batch-clear:hover {
  background: rgb(244, 63, 94, 0.1);
  color: #f43f5e;
}
.sub-batch-go {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 7px 16px;
  border-radius: var(--radius-btn);
  font-size: var(--text-2xs);
  font-weight: var(--font-medium);
  background: var(--accent-500);
  color: #fff;
  border: none;
  cursor: pointer;
  font-family: inherit;
}
.sub-batch-go:hover:not(:disabled) {
  opacity: 0.9;
}
.sub-batch-go:disabled {
  opacity: 0.4;
  cursor: default;
}
.glass-card {
  background: var(--surface-1);
  backdrop-filter: blur(16px);
  border: 0.5px solid var(--border-default);
  border-radius: var(--radius-card);
}
</style>
