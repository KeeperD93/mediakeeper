<template>
  <section class="params-section">
    <h3 class="params-section-title">{{ $t('backup.retentionTitle') }}</h3>
    <p class="params-section-desc">{{ $t('backup.retentionDesc') }}</p>
    <div class="backup-retention-row">
      <select
        class="backup-retention-select"
        :value="retentionMode"
        @change="emit('mode-change', $event.target.value)"
      >
        <option value="days">{{ $t('backup.retentionByDays') }}</option>
        <option value="count">{{ $t('backup.retentionByCount') }}</option>
        <option value="off">{{ $t('backup.retentionOff') }}</option>
      </select>
      <template v-if="retentionMode === 'days'">
        <input
          :value="retentionDays"
          type="number"
          min="1"
          max="365"
          class="backup-retention-input"
          @input="emit('update:retentionDays', Number($event.target.value))"
        />
        <span class="backup-retention-unit">{{ $t('backup.retentionDaysUnit') }}</span>
      </template>
      <template v-if="retentionMode === 'count'">
        <input
          :value="retentionCount"
          type="number"
          min="1"
          max="100"
          class="backup-retention-input"
          @input="emit('update:retentionCount', Number($event.target.value))"
        />
        <span class="backup-retention-unit">{{ $t('backup.retentionCountUnit') }}</span>
      </template>
      <button class="backup-retention-save" @click="emit('save')">
        {{ $t('common.save') }}
      </button>
    </div>
  </section>
</template>

<script setup>
defineProps({
  retentionMode: { type: String, default: 'days' },
  retentionDays: { type: Number, default: 30 },
  retentionCount: { type: Number, default: 10 },
})
const emit = defineEmits(['mode-change', 'update:retentionDays', 'update:retentionCount', 'save'])
</script>

<style scoped>
.backup-retention-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  padding: 12px 14px;
  background: var(--bg-primary);
  border: 0.5px solid var(--border);
  border-radius: var(--radius-btn);
}
.backup-retention-select {
  padding: 7px 12px;
  border-radius: var(--radius-sm);
  border: 0.5px solid var(--border);
  background: var(--bg-secondary);
  color: var(--text-primary);
  font-size: var(--text-sm);
  font-family: inherit;
  cursor: pointer;
}
.backup-retention-input {
  width: 70px;
  padding: 7px 10px;
  border-radius: var(--radius-sm);
  border: 0.5px solid var(--border);
  background: var(--bg-secondary);
  color: var(--text-primary);
  font-size: var(--text-sm);
  font-family: inherit;
  text-align: center;
}
.backup-retention-input:focus {
  outline: none;
  border-color: var(--accent-500);
}
.backup-retention-unit {
  font-size: var(--text-sm);
  color: var(--text-muted);
}
.backup-retention-save {
  padding: 7px 16px;
  border-radius: var(--radius-sm);
  background: var(--accent-600);
  color: var(--text-primary);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  border: none;
  cursor: pointer;
  font-family: inherit;
  margin-left: auto;
}
.backup-retention-save:hover {
  background: var(--accent-500);
}
</style>
