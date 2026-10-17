import { ref, computed } from 'vue'
import { resolveApiError, useApi } from '@/composables/useApi'
import { useToast } from '@/composables/useToast'
import { TOAST_TYPE } from '@/constants/toast'
import {
  BACKUP_RETENTION_MAX_COUNT,
  BACKUP_RETENTION_MAX_DAYS,
  BACKUP_RETENTION_MODE,
} from '@/constants/backup'
import { useI18n } from 'vue-i18n'
import { useConfirm } from '@/composables/useConfirm'
import { localizedDateTime } from '@/utils/datetime'

const backupInfo = ref(null)
const backupLoading = ref(false)
const backupCreating = ref(false)
const backupRestoring = ref(null)
const backupDirs = ref([])
const backupDirInput = ref('/data/backups')
const retentionMode = ref(BACKUP_RETENTION_MODE.DAYS)
const retentionDays = ref(30)
const retentionCount = ref(10)
// Same parts as the scheduled backup (DEFAULT_COMPONENTS on the server), in
// the order the screen lists them: the optional log files last.
const selectedComponents = ref({
  settings: true,
  preferences: true,
  scheduler: true,
  watchlist: true,
  pg_dump: true,
  logs: false,
})
const backupDirLocked = computed(() => !!backupInfo.value?.backup_dir_locked)
let loadedOnce = false

function formatSize(bytes) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1024 / 1024).toFixed(2) + ' MB'
}
function formatBackupDate(iso) {
  return localizedDateTime(new Date(iso), {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function useParamsBackup() {
  const { apiGet, apiFetch } = useApi()
  const { showToast } = useToast()
  const { t } = useI18n()
  const mkConfirm = useConfirm()

  const COMPONENT_LABELS = computed(() => ({
    settings: t('backup.compSettings'),
    preferences: t('backup.compPreferences'),
    scheduler: t('backup.compScheduler'),
    watchlist: t('backup.compWatchlist'),
    logs: t('backup.compLogs'),
    pg_dump: t('backup.compPgDump'),
  }))

  // The server's code names the failure (backup not found, invalid archive…);
  // without one (no answer, bare status), the action says what failed.
  function showFailure(where, e, fallbackKey) {
    console.error(`[useParamsBackup.${where}]`, e)
    showToast(resolveApiError(e?.message, fallbackKey), TOAST_TYPE.ERR)
  }

  async function loadBackupInfo() {
    backupLoading.value = true
    try {
      const data = await apiGet('/api/backup/info')
      if (data) {
        backupInfo.value = data
        backupDirInput.value = data.backup_dir || '/data/backups'
        if (data.retention_days === 0) retentionMode.value = BACKUP_RETENTION_MODE.OFF
        else if (data.retention_days < 0) {
          retentionMode.value = BACKUP_RETENTION_MODE.COUNT
          retentionCount.value = Math.abs(data.retention_days)
        } else {
          retentionMode.value = BACKUP_RETENTION_MODE.DAYS
          retentionDays.value = data.retention_days
        }
      }
    } catch (e) {
      showFailure('loadBackupInfo', e, 'common.apiError.loadFailed')
    }
    backupLoading.value = false
  }

  async function loadBackupDirs() {
    try {
      const data = await apiGet('/api/backup/directories')
      if (Array.isArray(data)) backupDirs.value = data
    } catch (e) {
      // Only the folder suggestions are missing: log it, no toast.
      console.error('[useParamsBackup.loadBackupDirs]', e)
    }
  }

  function onRetentionModeChange(mode) {
    retentionMode.value = mode
  }

  async function saveRetention() {
    let days = 0
    if (retentionMode.value !== BACKUP_RETENTION_MODE.OFF) {
      // The server refuses anything outside the screen's range: say which one.
      const byDays = retentionMode.value === BACKUP_RETENTION_MODE.DAYS
      const value = byDays ? retentionDays.value || 30 : retentionCount.value || 10
      const max = byDays ? BACKUP_RETENTION_MAX_DAYS : BACKUP_RETENTION_MAX_COUNT
      if (!Number.isInteger(value) || value < 1 || value > max) {
        const key = byDays ? 'backup.retentionDaysRange' : 'backup.retentionCountRange'
        showToast(t(key, { max }), TOAST_TYPE.ERR)
        return
      }
      days = byDays ? value : -value
    }
    try {
      await apiFetch('/api/backup/retention', { method: 'POST', body: JSON.stringify({ days }) })
      showToast(t('backup.retentionSaved'), TOAST_TYPE.OK)
    } catch (e) {
      showFailure('saveRetention', e, 'backup.retentionSaveFailed')
    }
  }

  async function changeBackupDir(dir) {
    try {
      const res = await apiFetch('/api/backup/set-directory', {
        method: 'POST',
        body: JSON.stringify({ path: dir }),
      })
      const data = await res.json()
      if (data.success) {
        showToast(t('backup.dirChanged'), TOAST_TYPE.OK)
        await loadBackupInfo()
      } else showToast(resolveApiError(data.detail, 'backup.dirChangeFailed'), TOAST_TYPE.ERR)
    } catch (e) {
      // BACKUP_PATH lock returns a dedicated code: say why the directory is
      // locked rather than that the change failed.
      if (e?.message === 'backup_directory_locked') {
        showToast(t('backup.dirLocked'), TOAST_TYPE.ERR)
        return
      }
      showFailure('changeBackupDir', e, 'backup.dirChangeFailed')
    }
  }

  async function createBackup() {
    backupCreating.value = true
    try {
      const res = await apiFetch('/api/backup/create', {
        method: 'POST',
        body: JSON.stringify({ components: selectedComponents.value, label: '' }),
      })
      const data = await res.json()
      if (data.success) {
        // The archive exists but lacks the parts whose export failed: name them.
        const missing = (data.failed_components || []).map(c => COMPONENT_LABELS.value[c] || c)
        if (missing.length) {
          showToast(t('backup.createdIncomplete', { parts: missing.join(', ') }), TOAST_TYPE.WARN)
        } else {
          showToast(t('backup.created'), TOAST_TYPE.OK)
        }
        await loadBackupInfo()
      }
    } catch (e) {
      showFailure('createBackup', e, 'common.apiError.backup_create_failed')
    }
    backupCreating.value = false
  }

  function downloadBackup(filename) {
    window.open('/api/backup/download/' + filename, '_blank')
  }

  async function deleteBackup(filename) {
    const ok = await mkConfirm({
      title: t('common.confirmTitle.delete'),
      message: t('backup.deleteConfirm'),
      variant: 'danger',
      confirmLabel: t('common.delete'),
    })
    if (!ok) return
    try {
      const res = await apiFetch('/api/backup/' + filename, { method: 'DELETE' })
      const data = await res.json()
      if (data.success) {
        showToast(t('backup.deleted'), TOAST_TYPE.OK)
        await loadBackupInfo()
      }
    } catch (e) {
      showFailure('deleteBackup', e, 'common.apiError.deleteFailed')
    }
  }

  async function restoreBackup(filename) {
    const ok = await mkConfirm({
      title: t('common.confirmTitle.restore'),
      message: t('backup.restoreConfirm'),
      variant: 'warn',
    })
    if (!ok) return
    backupRestoring.value = filename
    try {
      const res = await apiFetch('/api/backup/restore', {
        method: 'POST',
        body: JSON.stringify({ filename, components: selectedComponents.value }),
      })
      const data = await res.json()
      if (data.success) showToast(t('backup.restored'), TOAST_TYPE.OK)
      else showToast(t('common.apiError.backup_restore_failed'), TOAST_TYPE.ERR)
    } catch (e) {
      showFailure('restoreBackup', e, 'common.apiError.backup_restore_failed')
    }
    backupRestoring.value = null
  }

  async function uploadRestore(e) {
    const file = e.target.files[0]
    if (!file) return
    const isJson = file.name.endsWith('.json')
    const fd = new FormData()
    fd.append('file', file)
    fd.append('components', JSON.stringify(selectedComponents.value))
    try {
      const endpoint = isJson ? '/api/backup/upload-restore-json' : '/api/backup/upload-restore'
      const res = await apiFetch(endpoint, { method: 'POST', body: fd })
      const data = res ? await res.json() : null
      if (data?.success) {
        showToast(t('backup.restored'), TOAST_TYPE.OK)
        await loadBackupInfo()
      } else {
        const message = resolveApiError(data?.detail, 'common.apiError.backup_restore_failed')
        showToast(message, TOAST_TYPE.ERR)
      }
    } catch (err) {
      showFailure('uploadRestore', err, 'common.apiError.backup_restore_failed')
    }
    e.target.value = ''
  }

  async function ensureLoaded() {
    if (loadedOnce) return
    loadedOnce = true
    await Promise.all([loadBackupInfo(), loadBackupDirs()])
  }

  return {
    backupInfo,
    backupLoading,
    backupCreating,
    backupRestoring,
    backupDirs,
    backupDirInput,
    backupDirLocked,
    retentionMode,
    retentionDays,
    retentionCount,
    selectedComponents,
    COMPONENT_LABELS,
    formatSize,
    formatBackupDate,
    ensureLoaded,
    loadBackupInfo,
    loadBackupDirs,
    onRetentionModeChange,
    saveRetention,
    changeBackupDir,
    createBackup,
    downloadBackup,
    deleteBackup,
    restoreBackup,
    uploadRestore,
  }
}
