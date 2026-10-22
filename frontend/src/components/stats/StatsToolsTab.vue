<template>
  <div class="tab-panel">
    <div class="tools-grid">
      <div class="glass-card tool-card">
        <div class="tool-head">
          <Upload :size="18" class="tool-ico-accent" />
          <h3 class="tool-title">{{ $t('stats.importJellystats') }}</h3>
        </div>
        <p class="tool-desc">{{ $t('stats.importBackupDesc') }}</p>
        <label class="tool-btn-accent">
          <Plus :size="14" />
          {{ $t('stats.chooseFile') }}
          <input type="file" accept=".json" class="tool-file-hidden" @change="onFilePicked" />
        </label>
        <div v-if="importStatus" class="tool-status" :class="importStatus.type">
          {{ importStatus.text }}
        </div>
      </div>
      <div class="glass-card tool-card">
        <div class="tool-head">
          <Trash2 :size="18" class="tool-ico-danger" />
          <h3 class="tool-title">{{ $t('stats.purge') }}</h3>
        </div>
        <p class="tool-desc">{{ $t('stats.purgeDesc') }}</p>
        <MkButton variant="danger" icon="trash-2" @click="purgeJellystats">
          {{ $t('stats.purgeBtn') }}
        </MkButton>
        <div v-if="purgeStatus" class="tool-status" :class="purgeStatus.type">
          {{ purgeStatus.text }}
        </div>
      </div>
      <div class="glass-card tool-card">
        <div class="tool-head">
          <RefreshCw :size="18" class="tool-ico-accent" />
          <h3 class="tool-title">{{ $t('stats.migration') }}</h3>
        </div>
        <p class="tool-desc">{{ $t('stats.migrationDesc') }}</p>
        <MkButton variant="primary" icon="refresh-cw" @click="repairLibraryNames">
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
      <div class="excl-add">
        <select v-model="exclMode" class="excl-sel mk-select-chevron">
          <option :value="STATS_EXCLUSION_MODE.EXACT">{{ $t('stats.exact') }}</option>
          <option :value="STATS_EXCLUSION_MODE.CONTAINS">{{ $t('stats.contains') }}</option>
        </select>
        <input
          v-model="exclValue"
          class="excl-input"
          :placeholder="$t('stats.titlePlaceholder')"
          @keydown.enter="addExclusion"
        />
        <MkButton variant="icon" icon="plus" :aria-label="$t('common.add')" @click="addExclusion" />
      </div>
      <div v-if="exclusionsFailed && !exclusions.length" class="excl-empty">
        {{ $t('stats.exclusionsLoadError') }}
        <MkButton variant="link" size="sm" class="mk-touch-mobile" @click="loadExclusions">
          {{ $t('stats.retry') }}
        </MkButton>
      </div>
      <div v-else-if="!exclusions.length" class="excl-empty">{{ $t('stats.noExclusions') }}</div>
      <div v-for="(exc, i) in exclusions" :key="i" class="excl-item">
        <span class="excl-badge">
          {{ exc.mode === STATS_EXCLUSION_MODE.EXACT ? $t('stats.exact') : $t('stats.contains') }}
        </span>
        <span class="excl-val">{{ exc.value }}</span>
        <MkButton
          variant="icon"
          icon="x"
          size="sm"
          :aria-label="$t('common.remove')"
          @click="removeExclusion(i)"
        />
      </div>
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
import { onMounted } from 'vue'
import { Ban, Plus, RefreshCw, Trash2, Upload } from 'lucide-vue-next'
import MkButton from '@/components/common/MkButton.vue'
import StatsRepairOverlay from '@/components/stats/StatsRepairOverlay.vue'
import { useStatsTools } from '@/composables/useStatsTools'
import { STATS_EXCLUSION_MODE } from '@/constants/stats'

const {
  importStatus,
  purgeStatus,
  repairOpen,
  repairRunning,
  repairResult,
  repairError,
  exclusions,
  exclusionsFailed,
  exclMode,
  exclValue,
  importJellystats,
  purgeJellystats,
  repairLibraryNames,
  loadExclusions,
  addExclusion,
  removeExclusion,
} = useStatsTools()

// Cleared once the import ends: the same file can then be imported again, but
// picking it again mid-upload starts no second import.
async function onFilePicked(e) {
  const file = e.target.files[0]
  if (file) await importJellystats(file)
  e.target.value = ''
}

onMounted(loadExclusions)
</script>

<style scoped>
.tools-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}
.tool-card {
  padding: 18px 20px;
}
.glass-card {
  background: var(--surface-1);
  backdrop-filter: blur(16px);
  border: 0.5px solid var(--border-default);
  border-radius: var(--radius-card);
}
.tool-head {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
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
  margin-bottom: 14px;
  line-height: var(--lh-normal);
}
.tool-btn-accent {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 7px 14px;
  border-radius: var(--radius-btn);
  font-size: var(--text-xs);
  font-weight: var(--font-regular);
  background: rgb(var(--accent-rgb), 0.15);
  color: var(--accent-400);
  border: 0.5px solid rgb(var(--accent-rgb), 0.2);
  cursor: pointer;
  transition: all var(--duration-fast);
}
.tool-status {
  margin-top: 10px;
  font-size: var(--text-2xs);
  padding: 6px 10px;
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

.excl-add {
  display: flex;
  gap: 6px;
  margin-bottom: 12px;
}
.excl-sel {
  height: 32px;
  width: 90px;
  padding: 0 28px 0 10px;
  border: 0.5px solid var(--border-strong);
  border-radius: var(--radius-btn);
  background-color: var(--surface-2);
  font-size: var(--text-2xs);
  font-family: inherit;
  color: var(--text-primary);
  cursor: pointer;
  outline: none;
  box-sizing: border-box;
}
.excl-sel option {
  background: var(--mk-chrome-bg);
  color: var(--text-primary);
}
.excl-input {
  flex: 1;
  min-width: 0;
  background: var(--surface-2);
  border: 0.5px solid var(--border-strong);
  border-radius: var(--radius-sm);
  padding: 5px 10px;
  font-size: var(--text-2xs);
  color: var(--text-primary);
  outline: none;
}
.excl-input:focus {
  border-color: var(--accent-500);
}
.excl-empty {
  font-size: var(--text-2xs);
  color: var(--text-muted);
  padding: 4px 0;
}
.excl-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 5px 6px;
  border-radius: var(--radius-sm);
}
.excl-badge {
  /* 0.58rem / 4px sit below the smallest text + radius tokens
     (--text-3xs 0.62rem, --radius-sm floor); deliberately fixed for this
     micro mode-badge, kept raw per the rule of 3 — not an oversight. */
  font-size: 0.58rem;
  padding: 2px 6px;
  border-radius: 4px;
  background: var(--surface-2);
  color: var(--text-muted);
  flex-shrink: 0;
}
.excl-val {
  flex: 1;
  font-size: var(--text-xs);
  color: var(--text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.tool-ico-accent {
  color: var(--accent-500);
}
.tool-ico-danger {
  color: var(--color-error);
}
.tool-file-hidden {
  display: none;
}
.tool-card-excl {
  margin-top: 14px;
}
@media (max-width: 1280px) {
  .tools-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@media (max-width: 768px) {
  .tools-grid {
    grid-template-columns: 1fr;
  }
}
/* Touch targets ≥ 44px on mobile for the exclusion controls + file picker. */
@media (max-width: 767px) {
  .excl-sel,
  .excl-input,
  .tool-btn-accent {
    min-height: 44px;
  }
}
@media (hover: hover) {
  .tool-btn-accent:hover {
    background: rgb(var(--accent-rgb), 0.25);
  }
  .excl-item:hover {
    background: var(--surface-1);
  }
}
</style>
