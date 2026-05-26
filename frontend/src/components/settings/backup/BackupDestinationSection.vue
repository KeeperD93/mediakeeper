<template>
  <section class="params-section">
    <h3 class="params-section-title">{{ $t('backup.destinationTitle') }}</h3>
    <p class="params-section-desc">{{ $t('backup.destinationDesc') }}</p>
    <div class="backup-dest-row">
      <div class="backup-dest-input-wrap">
        <Folder class="backup-dest-icon" :size="14" />
        <input
          :value="backupDirInput"
          type="text"
          class="backup-dest-input"
          @input="emit('update:backupDirInput', $event.target.value)"
          @keydown.enter="emit('change-dir', backupDirInput)"
        />
        <button
          class="backup-dest-save"
          :disabled="backupDirInput === currentDir"
          @click="emit('change-dir', backupDirInput)"
        >
          {{ $t('common.save') }}
        </button>
      </div>
      <div v-if="backupDirs.length" class="backup-dest-suggestions">
        <span class="backup-dest-suggestions-label">{{ $t('backup.availableDirs') }}</span>
        <button
          v-for="dir in backupDirs"
          :key="dir"
          class="backup-dest-suggestion"
          :class="{ active: dir === backupDirInput }"
          @click="emit('update:backupDirInput', dir)"
        >
          {{ dir }}
        </button>
      </div>
    </div>
  </section>
</template>

<script setup>
import { Folder } from 'lucide-vue-next'

defineProps({
  backupDirInput: { type: String, default: '' },
  currentDir: { type: String, default: '/data/backups' },
  backupDirs: { type: Array, default: () => [] },
})
const emit = defineEmits(['update:backupDirInput', 'change-dir'])
</script>

<style scoped>
.backup-dest-row {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.backup-dest-input-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 4px 4px 14px;
  background: var(--bg-primary);
  border: 0.5px solid var(--border);
  border-radius: var(--radius-btn);
}
.backup-dest-icon {
  color: var(--text-muted);
  flex-shrink: 0;
}
.backup-dest-input {
  flex: 1;
  border: none;
  background: transparent;
  color: var(--text-primary);
  font-size: var(--text-sm);
  font-family: monospace;
  padding: 6px 0;
  outline: none;
  min-width: 0;
}
.backup-dest-save {
  padding: 6px 14px;
  border-radius: var(--radius-sm);
  background: var(--accent-600);
  color: var(--text-primary);
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  border: none;
  cursor: pointer;
  font-family: inherit;
  flex-shrink: 0;
  transition: opacity var(--duration-fast);
}
.backup-dest-save:hover {
  background: var(--accent-500);
}
.backup-dest-save:disabled {
  opacity: 0.35;
  cursor: default;
}
.backup-dest-suggestions {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
.backup-dest-suggestions-label {
  font-size: var(--text-2xs);
  color: var(--text-muted);
}
.backup-dest-suggestion {
  padding: 4px 10px;
  border-radius: var(--radius-sm);
  border: 0.5px solid var(--border);
  background: var(--bg-secondary);
  color: var(--text-secondary);
  font-size: var(--text-2xs);
  font-family: monospace;
  cursor: pointer;
  transition: all var(--duration-fast);
}
.backup-dest-suggestion:hover {
  border-color: var(--border-hover);
  color: var(--text-primary);
}
.backup-dest-suggestion.active {
  border-color: var(--accent-500);
  color: var(--accent-400);
  background: rgb(var(--accent-rgb), 0.08);
}
</style>
