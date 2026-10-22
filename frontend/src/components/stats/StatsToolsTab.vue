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

.excl-add {
  display: flex;
  gap: var(--space-2);
  margin-bottom: var(--space-3);
}
/* Background and border of the admin reference menus (Notifications). */
.excl-sel {
  height: 32px;
  /* Fits its longest option, 90px at least: no font cuts a label. */
  width: auto;
  min-width: 90px;
  padding-block: 0;
  padding-left: var(--space-3);
  border: var(--border-width) solid var(--border);
  border-radius: var(--radius-btn);
  background-color: var(--bg-tertiary);
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
  background: var(--bg-tertiary);
  border: var(--border-width) solid var(--border);
  border-radius: var(--radius-sm);
  padding: var(--space-1) var(--space-2-5);
  font-size: var(--text-2xs);
  color: var(--text-primary);
  outline: none;
}
.excl-input:focus {
  border-color: var(--accent-500);
}
.excl-sel:focus-visible,
.excl-input:focus-visible {
  outline: var(--focus-ring);
  outline-offset: var(--focus-ring-offset);
}
/* iOS zooms into a field under 16px it focuses: 16px there only. */
@supports (-webkit-touch-callout: none) {
  .excl-sel,
  .excl-input {
    font-size: var(--text-md);
  }
}
.excl-empty {
  font-size: var(--text-2xs);
  color: var(--text-muted);
  padding: var(--space-1) 0;
}
.excl-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-sm);
}
.excl-badge {
  /* 0.58rem / 4px sit below the smallest text + radius tokens
     (--text-3xs 0.62rem, --radius-sm floor); deliberately fixed for this
     micro mode-badge, kept raw per the rule of 3 — not an oversight. */
  font-size: 0.58rem;
  padding: var(--space-half) var(--space-2);
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
/* Touch targets ≥ 44px on mobile for the exclusion controls + tool actions. */
@media (max-width: 767px) {
  .excl-sel,
  .excl-input,
  .tool-action {
    min-height: var(--touch-target);
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
