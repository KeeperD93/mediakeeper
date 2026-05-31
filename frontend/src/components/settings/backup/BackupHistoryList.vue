<template>
  <section class="params-section">
    <h3 class="params-section-title">{{ $t('backup.history') }} ({{ backups.length }})</h3>

    <div v-if="backupLoading" class="params-loading">
      <div v-for="i in 3" :key="i" class="params-skel" />
    </div>

    <div v-else-if="!backups.length" class="backup-empty">
      {{ $t('backup.empty') }}
    </div>

    <div v-else class="backup-list">
      <div v-for="b in backups" :key="b.filename" class="backup-item">
        <div class="backup-item-main">
          <div class="backup-item-name">
            {{ b.filename.replace('mediakeeper_backup_', '').replace('.zip', '') }}
            <span v-if="b.label" class="backup-label-tag">{{ b.label }}</span>
          </div>
          <div class="backup-item-meta">
            {{ formatBackupDate(b.created_at) }} · {{ formatSize(b.size_bytes) }}
          </div>
          <div class="backup-item-comps">
            <template v-for="(val, key) in b.components" :key="key">
              <span v-if="val" class="backup-comp-tag">{{ key }}</span>
            </template>
          </div>
        </div>
        <div class="backup-item-actions">
          <button
            class="backup-item-btn"
            :title="$t('common.download')"
            @click="emit('download', b.filename)"
          >
            <Download :size="13" />
          </button>
          <button
            class="backup-item-btn"
            :disabled="backupRestoring === b.filename"
            :title="$t('common.restore')"
            @click="emit('restore', b.filename)"
          >
            <RefreshCw :size="13" />
          </button>
          <button
            class="backup-item-btn backup-item-btn-del"
            :title="$t('common.delete')"
            @click="emit('delete', b.filename)"
          >
            <Trash2 :size="13" />
          </button>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { Download, RefreshCw, Trash2 } from 'lucide-vue-next'

defineProps({
  backups: { type: Array, default: () => [] },
  backupLoading: { type: Boolean, default: false },
  backupRestoring: { type: String, default: '' },
  formatSize: { type: Function, required: true },
  formatBackupDate: { type: Function, required: true },
})
const emit = defineEmits(['download', 'restore', 'delete'])
</script>

<style scoped>
.backup-empty {
  font-size: var(--text-sm);
  color: var(--text-muted);
  padding: 20px 0;
  text-align: center;
}
.backup-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.backup-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: var(--bg-secondary);
  border: 0.5px solid var(--border);
  border-radius: var(--radius-card);
}
.backup-item-main {
  flex: 1;
  min-width: 0;
}
.backup-item-name {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-primary);
  font-family: monospace;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.backup-label-tag {
  font-size: var(--text-3xs);
  padding: 1px 7px;
  border-radius: 5px;
  background: rgb(var(--accent-rgb), 0.1);
  color: var(--accent-400);
  margin-left: 6px;
  font-family: inherit;
}
.backup-item-meta {
  font-size: var(--text-2xs);
  color: var(--text-muted);
  margin-top: 2px;
}
.backup-item-comps {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
  margin-top: 4px;
}
.backup-comp-tag {
  font-size: var(--text-3xs);
  padding: 1px 6px;
  border-radius: 4px;
  background: var(--bg-primary);
  border: 0.5px solid var(--border);
  color: var(--text-muted);
}
.backup-item-actions {
  display: flex;
  gap: 5px;
  flex-shrink: 0;
}
.backup-item-btn {
  width: 28px;
  height: 28px;
  border-radius: var(--radius-sm);
  border: 0.5px solid var(--border);
  background: var(--bg-primary);
  color: var(--text-muted);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--duration-fast);
}
.backup-item-btn:hover {
  border-color: var(--border-hover);
  color: var(--text-primary);
}
.backup-item-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.backup-item-btn-del:hover {
  border-color: var(--color-error);
  color: var(--color-error);
  background: rgb(var(--color-error-rgb), 0.08);
}
</style>
