<template>
  <section class="params-section">
    <h3 class="params-section-title">{{ $t('backup.components') }}</h3>
    <div class="backup-components">
      <label v-for="(val, key) in selectedComponents" :key="key" class="backup-comp-row">
        <input
          :checked="val"
          type="checkbox"
          class="backup-checkbox"
          @change="emit('toggle', { key, checked: $event.target.checked })"
        />
        <div class="backup-comp-info">
          <span class="backup-comp-label">{{ componentLabels[key] }}</span>
          <span v-if="key === 'pg_dump'" class="backup-comp-hint">
            {{ $t('backup.pgDumpHint') }}
          </span>
          <span v-if="key === 'logs'" class="backup-comp-hint">{{ $t('backup.logsHint') }}</span>
        </div>
      </label>
    </div>
  </section>
</template>

<script setup>
defineProps({
  selectedComponents: { type: Object, required: true },
  componentLabels: { type: Object, required: true },
})
const emit = defineEmits(['toggle'])
</script>

<style scoped>
.backup-components {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 4px;
}
.backup-comp-row {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 14px;
  background: var(--bg-primary);
  border: 0.5px solid var(--border);
  border-radius: var(--radius-btn);
  cursor: pointer;
  transition: border-color var(--duration-fast);
}
.backup-comp-row:hover {
  border-color: var(--border-hover);
}
.backup-checkbox {
  width: 15px;
  height: 15px;
  accent-color: var(--accent-500);
  flex-shrink: 0;
  margin-top: 1px;
  cursor: pointer;
}
.backup-comp-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.backup-comp-label {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-primary);
}
.backup-comp-hint {
  font-size: var(--text-2xs);
  color: var(--text-muted);
}
</style>
