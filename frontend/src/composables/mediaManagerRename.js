import {
  apiFetch,
  showToast,
  _t,
  activeCat,
  filtered,
  checked,
  newNames,
  dragSrc,
  modalConfirm,
  expandedMode,
  renameHistory,
  _saveRenameHistory,
  fileRenameStatus,
  renameErrors,
  showRenameErrorsModal,
  selectedTmdb,
  setProgress,
  endProgress,
} from './mediaManagerState'
import { loadFiles, applyRenameInPlace } from './mediaManagerNavigation'
import { FILE_TYPE } from '@/constants/mediaManager'
import { TOAST_TYPE } from '@/constants/toast'
import { useConfirm } from '@/composables/useConfirm'

const mkConfirm = useConfirm()

// Lie les newNames orphelins (sans path, ex. issus d'« Ajouter saison »)
// aux fichiers source position par position, en préservant l'extension
// d'origine. Priorité aux fichiers cochés ; sinon on prend l'ordre visuel
// de la liste filtrée (alignement 1-à-1 avec la colonne de droite).
// Idempotent (les non-orphelins sont ignorés).
function _linkOrphansToCheckedSources() {
  const orphans = []
  newNames.value.forEach((n, i) => {
    if (!n.path) orphans.push(i)
  })
  if (!orphans.length) return
  const usedPaths = new Set(newNames.value.map(n => n.path).filter(Boolean))
  let sources
  if (checked.value.size) {
    sources = [...checked.value]
      .sort((a, b) => a - b)
      .map(i => filtered.value[i])
      .filter(f => f?.type === FILE_TYPE.FILE)
  } else {
    sources = filtered.value.filter(f => f?.type === FILE_TYPE.FILE && !usedPaths.has(f.path))
  }
  if (!sources.length) return
  const count = Math.min(orphans.length, sources.length)
  for (let k = 0; k < count; k++) {
    const f = sources[k]
    const n = newNames.value[orphans[k]]
    const fExt = f.name.includes('.') ? f.name.split('.').pop() : ''
    if (n.ext && fExt && n.ext !== fExt) {
      n.name = n.name.slice(0, -(n.ext.length + 1)) + '.' + fExt
      n.ext = fExt
    }
    n.path = f.path
    n.oldName = f.name
  }
}

// ─── RENOMMAGE BATCH ───
export function startRename() {
  _linkOrphansToCheckedSources()
  modalConfirm.value = { show: true, lines: newNames.value }
}
export function clearRenameErrors() {
  renameErrors.value = []
  showRenameErrorsModal.value = false
}

export async function execRename() {
  modalConfirm.value.show = false
  const toRename = newNames.value.filter(n => n.path && n.path !== '')
  if (!toRename.length) {
    showToast(_t('mediaManager.noFilesToRename'), TOAST_TYPE.ERR)
    return
  }
  const statusMap = {}
  toRename.forEach(n => {
    statusMap[n.path] = 'pending'
  })
  fileRenameStatus.value = { ...statusMap }
  setProgress(5)
  let ok = 0,
    errCount = 0
  const historyItems = []
  const errors = []
  for (let i = 0; i < toRename.length; i++) {
    const n = toRename[i]
    fileRenameStatus.value = { ...fileRenameStatus.value, [n.path]: 'renaming' }
    setProgress(5 + 90 * ((i + 1) / toRename.length))
    try {
      const res = await apiFetch('/api/media/rename-batch', {
        method: 'POST',
        body: JSON.stringify({
          items: [{ old_path: n.path, new_name: n.name }],
          cat: activeCat.value,
        }),
      })
      const results = await res.json()
      if (results[0]?.success) {
        fileRenameStatus.value = { ...fileRenameStatus.value, [n.path]: 'done' }
        historyItems.push({
          oldName: n.oldName,
          newName: n.name,
          path: n.path,
          newPath: results[0].new_path || '',
        })
        applyRenameInPlace(n.path, n.name, results[0].new_path)
        ok++
      } else {
        fileRenameStatus.value = { ...fileRenameStatus.value, [n.path]: 'error' }
        errors.push({
          oldName: n.oldName,
          newName: n.name,
          path: n.path,
          reason: results[0]?.error || results[0]?.message || _t('common.unknownError'),
        })
        errCount++
      }
    } catch (e) {
      fileRenameStatus.value = { ...fileRenameStatus.value, [n.path]: 'error' }
      errors.push({
        oldName: n.oldName,
        newName: n.name,
        path: n.path,
        reason: e?.message || _t('common.networkError'),
      })
      errCount++
    }
  }
  if (historyItems.length > 0) {
    renameHistory.value.unshift({
      timestamp: Date.now(),
      cat: activeCat.value,
      tmdbTitle: selectedTmdb.value?.title || '',
      items: historyItems,
    })
    _saveRenameHistory()
  }
  endProgress()
  setTimeout(() => {
    fileRenameStatus.value = {}
  }, 2000)
  newNames.value = []
  expandedMode.value = false
  if (errCount > 0) {
    renameErrors.value = errors
    showRenameErrorsModal.value = true
    showToast(_t('mediaManager.renameResult', { ok, errors: errCount }), TOAST_TYPE.ERR)
  } else {
    showToast(_t('mediaManager.filesRenamed', { count: ok }), TOAST_TYPE.OK)
  }
  // Resync from disk so subsequent moves use fresh paths. The in-place
  // updates above keep the row order stable mid-batch, but file/folder
  // names on the NAS are the source of truth for any next operation.
  if (ok > 0) loadFiles()
}

// ─── UNDO RENAME ───
export async function undoRename(historyIdx) {
  const entry = renameHistory.value[historyIdx]
  if (!entry?.items?.length) return
  const confirmed = await mkConfirm({
    title: _t('common.confirmTitle.cancel'),
    message: _t('mediaManager.cancelRenameConfirm', { count: entry.items.length }),
    variant: 'warn',
  })
  if (!confirmed) return
  setProgress(5)
  let ok = 0,
    err = 0
  for (let i = 0; i < entry.items.length; i++) {
    const item = entry.items[i]
    setProgress(5 + 90 * ((i + 1) / entry.items.length))
    const undoPath = item.newPath || item.path.replace(/[^/]+$/, item.newName)
    try {
      const res = await apiFetch('/api/media/rename-batch', {
        method: 'POST',
        body: JSON.stringify({
          items: [{ old_path: undoPath, new_name: item.oldName }],
          cat: entry.cat,
        }),
      })
      const results = await res.json()
      if (results[0]?.success) ok++
      else err++
    } catch {
      err++
    }
  }
  endProgress()
  if (ok > 0) {
    renameHistory.value.splice(historyIdx, 1)
    _saveRenameHistory()
  }
  showToast(
    err === 0
      ? _t('mediaManager.filesRestored', { count: ok })
      : _t('mediaManager.partialResult', { ok, errors: err }),
    err === 0 ? TOAST_TYPE.OK : TOAST_TYPE.ERR,
  )
  loadFiles()
}
export function clearRenameHistory() {
  renameHistory.value = []
  _saveRenameHistory()
  showToast(_t('mediaManager.historyCleared'), TOAST_TYPE.OK)
}

// Drag-to-reorder (colonne right uniquement)
export function dStart(i) {
  dragSrc.value = i
}
export function dDrop(toI) {
  if (dragSrc.value === null || dragSrc.value === toI) {
    dragSrc.value = null
    return
  }
  const m = newNames.value.splice(dragSrc.value, 1)[0]
  newNames.value.splice(toI, 0, m)
  dragSrc.value = null
}
export function removeRight(i) {
  newNames.value.splice(i, 1)
}
export function clearRight() {
  newNames.value = []
}
