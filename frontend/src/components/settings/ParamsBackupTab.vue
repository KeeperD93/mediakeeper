<template>
  <div>
    <h2 class="params-title">{{ $t('settings.tabBackup') }}</h2>
    <p class="params-desc">{{ $t('backup.desc') }}</p>

    <BackupComponentsSection
      :selected-components="selectedComponents"
      :component-labels="COMPONENT_LABELS"
      @toggle="onComponentToggle"
    />

    <BackupActions
      :backup-creating="backupCreating"
      @create="createBackup"
      @upload="uploadRestore"
    />

    <BackupDestinationSection
      v-model:backup-dir-input="backupDirInput"
      :current-dir="backupInfo?.backup_dir || '/data/backups'"
      :backup-dirs="backupDirs"
      @change-dir="changeBackupDir"
    />

    <BackupRetentionSection
      v-model:retention-days="retentionDays"
      v-model:retention-count="retentionCount"
      :retention-mode="retentionMode"
      @mode-change="onRetentionModeChange"
      @save="saveRetention"
    />

    <BackupHistoryList
      :backups="backupInfo?.backups || []"
      :backup-loading="backupLoading"
      :backup-restoring="backupRestoring"
      :format-size="formatSize"
      :format-backup-date="formatBackupDate"
      @download="downloadBackup"
      @restore="restoreBackup"
      @delete="deleteBackup"
    />
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useParamsBackup } from '@/composables/useParamsBackup'
import BackupComponentsSection from './backup/BackupComponentsSection.vue'
import BackupActions from './backup/BackupActions.vue'
import BackupDestinationSection from './backup/BackupDestinationSection.vue'
import BackupRetentionSection from './backup/BackupRetentionSection.vue'
import BackupHistoryList from './backup/BackupHistoryList.vue'

const {
  backupInfo,
  backupLoading,
  backupCreating,
  backupRestoring,
  backupDirs,
  backupDirInput,
  retentionMode,
  retentionDays,
  retentionCount,
  selectedComponents,
  COMPONENT_LABELS,
  formatSize,
  formatBackupDate,
  ensureLoaded,
  onRetentionModeChange,
  saveRetention,
  changeBackupDir,
  createBackup,
  downloadBackup,
  deleteBackup,
  restoreBackup,
  uploadRestore,
} = useParamsBackup()

function onComponentToggle({ key, checked }) {
  selectedComponents.value[key] = checked
}

onMounted(ensureLoaded)
</script>
