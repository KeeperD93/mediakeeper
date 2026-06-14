import { ref, computed } from 'vue'
import { useApi } from '@/composables/useApi'
import { useToast } from '@/composables/useToast'
import { TOAST_TYPE } from '@/constants/toast'
import { useI18n } from 'vue-i18n'
import { useConfirm } from '@/composables/useConfirm'
import { localizedDateTime } from '@/utils/datetime'

const backupInfo = ref(null)
const backupLoading = ref(false)
const backupCreating = ref(false)
const backupRestoring = ref(null)
const backupDirs = ref([])
const backupDirInput = ref('/data/backups')
const retentionMode = ref('days')
const retentionDays = ref(30)
const retentionCount = ref(10)
const selectedComponents = ref({
  settings: true,
  preferences: true,
  scheduler: true,
  watchlist: true,
  logs: false,
  pg_dump: false,
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

  async function loadBackupInfo() {
    backupLoading.value = true
    try {
      const data = await apiGet('/api/backup/info')
      if (data) {
        backupInfo.value = data
        backupDirInput.value = data.backup_dir || '/data/backups'
        if (data.retention_days === 0) retentionMode.value = 'off'
        else if (data.retention_days < 0) {
          retentionMode.value = 'count'
          retentionCount.value = Math.abs(data.retention_days)
        } else {
          retentionMode.value = 'days'
          retentionDays.value = data.retention_days
        }
      }
    } catch {
      /* silent: backup info load, UI stays empty */
    }
    backupLoading.value = false
  }

  async function loadBackupDirs() {
    try {
      const data = await apiGet('/api/backup/directories')
      if (Array.isArray(data)) backupDirs.value = data
    } catch {
      /* silent: backup dirs load */
    }
  }

  function onRetentionModeChange(mode) {
    retentionMode.value = mode
  }

  async function saveRetention() {
    let days = 0
    if (retentionMode.value === 'days') days = retentionDays.value || 30
    else if (retentionMode.value === 'count') days = -(retentionCount.value || 10)
    try {
      await apiFetch('/api/backup/retention', { method: 'POST', body: JSON.stringify({ days }) })
      showToast(t('backup.retentionSaved'), TOAST_TYPE.OK)
    } catch {
      showToast(t('common.networkError'), TOAST_TYPE.ERR)
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
      } else showToast(data.detail || t('common.networkError'), TOAST_TYPE.ERR)
    } catch (e) {
      // BACKUP_PATH lock returns a dedicated code — explain it rather than
      // surfacing a generic network error.
      if (e?.message === 'backup_directory_locked') {
        showToast(t('backup.dirLocked'), TOAST_TYPE.ERR)
        return
      }
      console.error('[useParamsBackup.changeBackupDir] failed to change backup directory', e)
      showToast(t('common.networkError'), TOAST_TYPE.ERR)
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
        showToast(t('backup.created'), TOAST_TYPE.OK)
        await loadBackupInfo()
      }
    } catch {
      showToast(t('common.networkError'), TOAST_TYPE.ERR)
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
    const res = await apiFetch('/api/backup/' + filename, { method: 'DELETE' })
    const data = await res.json()
    if (data.success) {
      showToast(t('backup.deleted'), TOAST_TYPE.OK)
      await loadBackupInfo()
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
      else showToast(t('common.networkError'), TOAST_TYPE.ERR)
    } catch {
      showToast(t('common.networkError'), TOAST_TYPE.ERR)
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
      } else showToast(data?.detail || t('common.networkError'), TOAST_TYPE.ERR)
    } catch {
      showToast(t('common.networkError'), TOAST_TYPE.ERR)
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
