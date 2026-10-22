<template>
  <div class="tab-panel">
    <div class="tools-grid">
      <div class="glass-card tool-card">
        <div class="tool-head">
          <Upload :size="18" class="tool-ico-accent" />
          <h3 class="tool-title">{{ $t('stats.importJellystats') }}</h3>
        </div>
        <p class="tool-desc">{{ $t('stats.importBackupDesc') }}</p>
        <div role="status">
          <div v-if="importStatus" class="tool-status" :class="importStatus.type">
            {{ importStatus.text }}
          </div>
        </div>
        <label class="tool-btn-accent tool-action">
          <Plus :size="14" />
          {{ $t('stats.chooseFile') }}
          <input type="file" accept=".json" class="sr-only" @change="onFilePicked" />
        </label>
      </div>
      <div class="glass-card tool-card">
        <div class="tool-head">
          <Trash2 :size="18" class="tool-ico-danger" />
          <h3 class="tool-title">{{ $t('stats.purge') }}</h3>
        </div>
        <p class="tool-desc">{{ $t('stats.purgeDesc') }}</p>
        <div role="status">
          <div v-if="purgeStatus" class="tool-status" :class="purgeStatus.type">
            {{ purgeStatus.text }}
          </div>
        </div>
        <MkButton class="tool-action" variant="danger" icon="trash-2" @click="purgeJellystats">
          {{ $t('stats.purgeBtn') }}
        </MkButton>
      </div>
      <div class="glass-card tool-card">
        <div class="tool-head">
          <RefreshCw :size="18" class="tool-ico-accent" />
          <h3 class="tool-title">{{ $t('stats.migration') }}</h3>
        </div>
        <p class="tool-desc">{{ $t('stats.migrationDesc') }}</p>
        <MkButton
          class="tool-action"
          variant="primary"
          icon="refresh-cw"
          @click="repairLibraryNames"
        >
          {{ $t('stats.launch') }}
        </MkButton>
      </div>
    </div>
    <div class="glass-card tool-card tool-card-excl">
      <div class="tool-head">
        <Ban :size="18" class="tool-ico-accent" />
        <h3 class="tool-title">{{ $t('stats.exclusions') }}</h3>
      </div>
      <p class="tool-desc">{{ $t('stats.exclusionsDesc') }}</p>
      <StatsExclusions />
    </div>

    <StatsRepairOverlay
      :open="repairOpen"
      :running="repairRunning"
      :result="repairResult"
      :error="repairError"
      @close="repairOpen = false"
    />
  </div>
</template>

<script setup>
import { Ban, Plus, RefreshCw, Trash2, Upload } from 'lucide-vue-next'
import MkButton from '@/components/common/MkButton.vue'
import StatsExclusions from '@/components/stats/StatsExclusions.vue'
import StatsRepairOverlay from '@/components/stats/StatsRepairOverlay.vue'
import { useStatsTools } from '@/composables/useStatsTools'

const {
  importStatus,
  purgeStatus,
  repairOpen,
  repairRunning,
  repairResult,
  repairError,
  importJellystats,
  purgeJellystats,
  repairLibraryNames,
} = useStatsTools()

// Cleared once the import ends: the same file can then be imported again, but
// picking it again mid-upload starts no second import.
async function onFilePicked(e) {
  const file = e.target.files[0]
  if (file) await importJellystats(file)
  e.target.value = ''
}
</script>

<style scoped>
.tools-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-3);
}
.tool-card {
  padding: var(--space-5);
}
/* Grid cards share a row height; the text takes the spare room so the
   status and the action sit at the bottom-left. */
.tools-grid > .tool-card {
  display: flex;
  flex-direction: column;
}
.tools-grid > .tool-card > .tool-desc {
  flex-grow: 1;
}
.tool-action {
  align-self: flex-start;
}
.glass-card {
  background: var(--surface-1);
  backdrop-filter: blur(16px);
  border: var(--border-width-thin) solid var(--border-default);
  border-radius: var(--radius-card);
}
.tool-head {
  display: flex;
  align-items: center;
  gap: var(--space-2-5);
  margin-bottom: var(--space-2-5);
}
.tool-title {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-primary);
  margin: 0;
}
.tool-desc {
  font-size: var(--text-2xs);
  color: var(--text-secondary);
  margin-bottom: var(--space-5);
  line-height: var(--lh-normal);
}
.tool-btn-accent {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3-5);
  border-radius: var(--radius-btn);
  font-size: var(--text-xs);
  font-weight: var(--font-regular);
  background: rgb(var(--accent-rgb), 0.15);
  color: var(--accent-400);
  border: var(--border-width-thin) solid rgb(var(--accent-rgb), 0.2);
  cursor: pointer;
  transition: var(--transition-bg);
}
/* The file input is visually hidden but focusable: the label shows its focus. */
.tool-btn-accent:has(:focus-visible) {
  outline: var(--focus-ring);
  outline-offset: var(--focus-ring-offset);
}
.tool-status {
  margin-bottom: var(--space-2-5);
  font-size: var(--text-2xs);
  padding: var(--space-2) var(--space-2-5);
  border-radius: var(--radius-sm);
}
.tool-status.info {
  background: rgb(var(--accent-rgb), 0.1);
  color: var(--accent-400);
}
.tool-status.ok {
  background: rgb(var(--color-success-rgb), 0.1);
  color: var(--color-success);
}
.tool-status.err {
  background: rgb(var(--color-error-rgb), 0.1);
  color: var(--color-error);
}

.tool-ico-accent {
  color: var(--accent-500);
}
.tool-ico-danger {
  color: var(--color-error);
}
.tool-card-excl {
  margin-top: var(--space-3-5);
}
@media (max-width: 1280px) {
  .tools-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@media (max-width: 768px) {
  .tools-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}
/* Touch targets ≥ 44px on mobile for the tool actions. */
@media (max-width: 767px) {
  .tool-action {
    min-height: var(--touch-target);
  }
}
@media (hover: hover) {
  .tool-btn-accent:hover {
    background: rgb(var(--accent-rgb), 0.25);
  }
}
</style>
