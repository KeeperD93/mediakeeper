<template>
  <div>
    <h2 class="params-title">{{ $t('settings.tabBackup') }}</h2>
    <p class="params-desc">{{ $t('backup.desc') }}</p>

    <section class="params-section">
      <h3 class="params-section-title">{{ $t('backup.components') }}</h3>
      <div class="backup-components">
        <label v-for="(val, key) in selectedComponents" :key="key" class="backup-comp-row">
          <input v-model="selectedComponents[key]" type="checkbox" class="backup-checkbox" />
          <div class="backup-comp-info">
            <span class="backup-comp-label">{{ COMPONENT_LABELS[key] }}</span>
            <span v-if="key === 'pg_dump'" class="backup-comp-hint">{{ $t('backup.pgDumpHint') }}</span>
            <span v-if="key === 'logs'" class="backup-comp-hint">{{ $t('backup.logsHint') }}</span>
          </div>
        </label>
      </div>
    </section>

    <section class="params-section">
      <h3 class="params-section-title">{{ $t('backup.actions') }}</h3>
      <div class="backup-actions">
        <button class="backup-action-btn backup-btn-create" :disabled="backupCreating" @click="createBackup">
          <span v-if="backupCreating" class="mk-spin mk-spin-14 backup-spin-white" />
          <CloudDownload v-else :size="15" />
          {{ $t('backup.createNow') }}
        </button>
        <label class="backup-action-btn backup-btn-upload">
          <input type="file" accept=".zip,.json" class="backup-file-hidden" @change="uploadRestore" />
          <Upload :size="15" />
          {{ $t('backup.uploadRestore') }}
        </label>
      </div>
    </section>

    <section class="params-section">
      <h3 class="params-section-title">{{ $t('backup.destinationTitle') }}</h3>
      <p class="params-section-desc">{{ $t('backup.destinationDesc') }}</p>
      <div class="backup-dest-row">
        <div class="backup-dest-input-wrap">
          <Folder class="backup-dest-icon" :size="14" />
          <input v-model="backupDirInput" type="text" class="backup-dest-input" @keydown.enter="changeBackupDir(backupDirInput)" />
          <button class="backup-dest-save" :disabled="backupDirInput === (backupInfo?.backup_dir || '/data/backups')" @click="changeBackupDir(backupDirInput)">
            {{ $t('common.save') }}
          </button>
        </div>
        <div v-if="backupDirs.length" class="backup-dest-suggestions">
          <span class="backup-dest-suggestions-label">{{ $t('backup.availableDirs') }}</span>
          <button v-for="dir in backupDirs" :key="dir" class="backup-dest-suggestion" :class="{ active: dir === backupDirInput }" @click="backupDirInput = dir">
            {{ dir }}
          </button>
        </div>
      </div>
    </section>

    <section class="params-section">
      <h3 class="params-section-title">{{ $t('backup.retentionTitle') }}</h3>
      <p class="params-section-desc">{{ $t('backup.retentionDesc') }}</p>
      <div class="backup-retention-row">
        <select class="backup-retention-select" :value="retentionMode" @change="onRetentionModeChange($event.target.value)">
          <option value="days">{{ $t('backup.retentionByDays') }}</option>
          <option value="count">{{ $t('backup.retentionByCount') }}</option>
          <option value="off">{{ $t('backup.retentionOff') }}</option>
        </select>
        <template v-if="retentionMode === 'days'">
          <input v-model.number="retentionDays" type="number" min="1" max="365" class="backup-retention-input" />
          <span class="backup-retention-unit">{{ $t('backup.retentionDaysUnit') }}</span>
        </template>
        <template v-if="retentionMode === 'count'">
          <input v-model.number="retentionCount" type="number" min="1" max="100" class="backup-retention-input" />
          <span class="backup-retention-unit">{{ $t('backup.retentionCountUnit') }}</span>
        </template>
        <button class="backup-retention-save" @click="saveRetention">{{ $t('common.save') }}</button>
      </div>
    </section>

    <section class="params-section">
      <h3 class="params-section-title">{{ $t('backup.history') }} ({{ backupInfo?.backups?.length || 0 }})</h3>

      <div v-if="backupLoading" class="params-loading">
        <div v-for="i in 3" :key="i" class="params-skel" />
      </div>

      <div v-else-if="!backupInfo?.backups?.length" class="backup-empty">
        {{ $t('backup.empty') }}
      </div>

      <div v-else class="backup-list">
        <div v-for="b in backupInfo.backups" :key="b.filename" class="backup-item">
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
            <button class="backup-item-btn" :title="$t('common.download')" @click="downloadBackup(b.filename)">
              <Download :size="13" />
            </button>
            <button class="backup-item-btn" :disabled="backupRestoring === b.filename" :title="$t('common.restore')" @click="restoreBackup(b.filename)">
              <RefreshCw :size="13" />
            </button>
            <button class="backup-item-btn backup-item-btn-del" :title="$t('common.delete')" @click="deleteBackup(b.filename)">
              <Trash2 :size="13" />
            </button>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useParamsBackup } from '@/composables/useParamsBackup'
import { CloudDownload, Download, Folder, RefreshCw, Trash2, Upload } from 'lucide-vue-next'

const {
  backupInfo, backupLoading, backupCreating, backupRestoring,
  backupDirs, backupDirInput,
  retentionMode, retentionDays, retentionCount,
  selectedComponents, COMPONENT_LABELS,
  formatSize, formatBackupDate,
  ensureLoaded,
  onRetentionModeChange, saveRetention, changeBackupDir,
  createBackup, downloadBackup, deleteBackup, restoreBackup, uploadRestore,
} = useParamsBackup()

onMounted(ensureLoaded)
</script>

<style scoped>
.backup-components { display: flex; flex-direction: column; gap: 8px; margin-bottom: 4px; }
.backup-comp-row { display: flex; align-items: flex-start; gap: 10px; padding: 10px 14px; background: var(--bg-primary); border: .5px solid var(--border); border-radius: var(--radius-btn); cursor: pointer; transition: border-color var(--duration-fast); }
.backup-comp-row:hover { border-color: var(--border-hover); }
.backup-checkbox { width: 15px; height: 15px; accent-color: var(--accent-500); flex-shrink: 0; margin-top: 1px; cursor: pointer; }
.backup-comp-info { display: flex; flex-direction: column; gap: 2px; }
.backup-comp-label { font-size: var(--text-sm); font-weight: var(--font-medium); color: var(--text-primary); }
.backup-comp-hint { font-size: var(--text-2xs); color: var(--text-muted); }
.backup-actions { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 10px; }
.backup-action-btn { display: flex; align-items: center; gap: 8px; padding: 9px 18px; border-radius: var(--radius-btn); font-size: var(--text-sm); font-weight: var(--font-medium); cursor: pointer; font-family: inherit; border: none; transition: all var(--duration-fast); }
.backup-spin-white { border-color: rgba(255,255,255,.3); border-top-color: #fff; }
.backup-file-hidden { display: none; }
.backup-btn-create { background: var(--accent-600); color: #fff; }
.backup-btn-create:hover:not(:disabled) { background: var(--accent-500); }
.backup-btn-create:disabled { opacity: .5; cursor: not-allowed; }
.backup-btn-upload { background: var(--bg-secondary); border: .5px solid var(--border) !important; color: var(--text-secondary); cursor: pointer; }
.backup-btn-upload:hover { border-color: var(--border-hover) !important; color: var(--text-primary); }
.backup-empty { font-size: var(--text-sm); color: var(--text-muted); padding: 20px 0; text-align: center; }
.backup-list { display: flex; flex-direction: column; gap: 8px; }
.backup-item { display: flex; align-items: center; gap: 12px; padding: 12px 16px; background: var(--bg-secondary); border: .5px solid var(--border); border-radius: var(--radius-card); }
.backup-item-main { flex: 1; min-width: 0; }
.backup-item-name { font-size: var(--text-sm); font-weight: var(--font-medium); color: var(--text-primary); font-family: monospace; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.backup-label-tag { font-size: var(--text-3xs); padding: 1px 7px; border-radius: 5px; background: rgba(var(--accent-rgb),.1); color: var(--accent-400); margin-left: 6px; font-family: inherit; }
.backup-item-meta { font-size: var(--text-2xs); color: var(--text-muted); margin-top: 2px; }
.backup-item-comps { display: flex; gap: 4px; flex-wrap: wrap; margin-top: 4px; }
.backup-comp-tag { font-size: var(--text-3xs); padding: 1px 6px; border-radius: 4px; background: var(--bg-primary); border: .5px solid var(--border); color: var(--text-muted); }
.backup-item-actions { display: flex; gap: 5px; flex-shrink: 0; }
.backup-item-btn { width: 28px; height: 28px; border-radius: var(--radius-sm); border: .5px solid var(--border); background: var(--bg-primary); color: var(--text-muted); cursor: pointer; display: flex; align-items: center; justify-content: center; transition: all var(--duration-fast); }
.backup-item-btn:hover { border-color: var(--border-hover); color: var(--text-primary); }
.backup-item-btn:disabled { opacity: .4; cursor: not-allowed; }
.backup-item-btn-del:hover { border-color: var(--color-error); color: var(--color-error); background: rgba(var(--color-error-rgb),.08); }

.backup-dest-row { display: flex; flex-direction: column; gap: 10px; }
.backup-dest-input-wrap {
  display: flex; align-items: center; gap: 8px;
  padding: 4px 4px 4px 14px; background: var(--bg-primary);
  border: .5px solid var(--border); border-radius: var(--radius-btn);
}
.backup-dest-icon { color: var(--text-muted); flex-shrink: 0; }
.backup-dest-input {
  flex: 1; border: none; background: transparent;
  color: var(--text-primary); font-size: var(--text-sm); font-family: monospace;
  padding: 6px 0; outline: none; min-width: 0;
}
.backup-dest-save {
  padding: 6px 14px; border-radius: var(--radius-sm);
  background: var(--accent-600); color: #fff; font-size: var(--text-xs);
  font-weight: var(--font-medium); border: none; cursor: pointer; font-family: inherit;
  flex-shrink: 0; transition: opacity var(--duration-fast);
}
.backup-dest-save:hover { background: var(--accent-500); }
.backup-dest-save:disabled { opacity: .35; cursor: default; }
.backup-dest-suggestions { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.backup-dest-suggestions-label { font-size: var(--text-2xs); color: var(--text-muted); }
.backup-dest-suggestion {
  padding: 4px 10px; border-radius: var(--radius-sm);
  border: .5px solid var(--border); background: var(--bg-secondary);
  color: var(--text-secondary); font-size: var(--text-2xs); font-family: monospace;
  cursor: pointer; transition: all var(--duration-fast);
}
.backup-dest-suggestion:hover { border-color: var(--border-hover); color: var(--text-primary); }
.backup-dest-suggestion.active { border-color: var(--accent-500); color: var(--accent-400); background: rgba(var(--accent-rgb),.08); }

.backup-retention-row {
  display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
  padding: 12px 14px; background: var(--bg-primary);
  border: .5px solid var(--border); border-radius: var(--radius-btn);
}
.backup-retention-select {
  padding: 7px 12px; border-radius: var(--radius-sm);
  border: .5px solid var(--border); background: var(--bg-secondary);
  color: var(--text-primary); font-size: var(--text-sm); font-family: inherit;
  cursor: pointer;
}
.backup-retention-input {
  width: 70px; padding: 7px 10px; border-radius: var(--radius-sm);
  border: .5px solid var(--border); background: var(--bg-secondary);
  color: var(--text-primary); font-size: var(--text-sm); font-family: inherit;
  text-align: center;
}
.backup-retention-input:focus { outline: none; border-color: var(--accent-500); }
.backup-retention-unit { font-size: var(--text-sm); color: var(--text-muted); }
.backup-retention-save {
  padding: 7px 16px; border-radius: var(--radius-sm);
  background: var(--accent-600); color: #fff; font-size: var(--text-sm);
  font-weight: var(--font-medium); border: none; cursor: pointer; font-family: inherit;
  margin-left: auto;
}
.backup-retention-save:hover { background: var(--accent-500); }
</style>
