<template>
  <section class="params-section">
    <h3 class="params-section-title">{{ $t('backup.actions') }}</h3>
    <div class="backup-actions">
      <button
        class="backup-action-btn backup-btn-create"
        :disabled="backupCreating"
        @click="emit('create')"
      >
        <span v-if="backupCreating" class="mk-spin mk-spin-14 backup-spin-white" />
        <CloudDownload v-else :size="15" />
        {{ $t('backup.createNow') }}
      </button>
      <label class="backup-action-btn backup-btn-upload">
        <input
          type="file"
          accept=".zip,.json"
          class="backup-file-hidden"
          @change="emit('upload', $event)"
        />
        <Upload :size="15" />
        {{ $t('backup.uploadRestore') }}
      </label>
    </div>
  </section>
</template>

<script setup>
import { CloudDownload, Upload } from 'lucide-vue-next'

defineProps({
  backupCreating: { type: Boolean, default: false },
})
const emit = defineEmits(['create', 'upload'])
</script>

<style scoped>
.backup-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 10px;
}
.backup-action-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 18px;
  border-radius: var(--radius-btn);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  cursor: pointer;
  font-family: inherit;
  border: none;
  transition: all var(--duration-fast);
}
.backup-spin-white {
  border-color: rgb(255, 255, 255, 0.3);
  border-top-color: var(--text-primary);
}
.backup-file-hidden {
  display: none;
}
.backup-btn-create {
  background: var(--accent-600);
  color: var(--text-primary);
}
.backup-btn-create:hover:not(:disabled) {
  background: var(--accent-500);
}
.backup-btn-create:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.backup-btn-upload {
  background: var(--bg-secondary);
  border: 0.5px solid var(--border) !important;
  color: var(--text-secondary);
  cursor: pointer;
}
.backup-btn-upload:hover {
  border-color: var(--border-hover) !important;
  color: var(--text-primary);
}
</style>
