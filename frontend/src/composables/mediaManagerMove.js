import {
  apiGet,
  apiFetch,
  showToast,
  _t,
  activeCat,
  filtered,
  checked,
  dragFileIdx,
  dragIsGrouped,
  dragOverCat,
  moveConflicts,
  showMoveConflictModal,
  pendingMoveFiles,
  pendingMoveDest,
  moveHistory,
  _saveMoveHistory,
  setProgress,
  endProgress,
} from './mediaManagerState'
import { loadFiles } from './mediaManagerNavigation'
import { TOAST_TYPE } from '@/constants/toast'
import { FILE_TYPE } from '@/constants/mediaManager'

export function fileDragStart(idx) {
  dragIsGrouped.value = checked.value.has(idx) && checked.value.size > 1
  dragFileIdx.value = idx
}
export function fileDragEnd() {
  dragFileIdx.value = null
  dragOverCat.value = null
}

export async function dropOnCat(destCat) {
  if (dragFileIdx.value === null && !dragIsGrouped.value) {
    dragOverCat.value = null
    return
  }
  if (destCat === activeCat.value) {
    dragOverCat.value = null
    return
  }
  const filesToMove = []
  if (dragIsGrouped.value && checked.value.size > 0) {
    ;[...checked.value].forEach(i => {
      const f = filtered.value[i]
      if (f?.type === FILE_TYPE.FILE) filesToMove.push(f)
    })
    dragIsGrouped.value = false
  } else if (dragFileIdx.value !== null) {
    const f = filtered.value[dragFileIdx.value]
    if (f) filesToMove.push(f)
  }
  dragFileIdx.value = null
  dragOverCat.value = null
  if (!filesToMove.length) return
  try {
    const rootData = await apiGet(`/api/media/rootpath/${destCat}`)
    if (rootData?.error) {
      console.error('[mediaManagerMove.dropOnCategory] backend error', rootData.error)
      showToast(_t('common.apiError.unknown', { status: '' }), TOAST_TYPE.ERR)
      return
    }
    await _checkAndMove(filesToMove, rootData.path)
  } catch {
    showToast(_t('common.networkError'), TOAST_TYPE.ERR)
  }
}

export async function dropOnFolder(folderIdx) {
  if (dragFileIdx.value === null || dragFileIdx.value === folderIdx) return
  const dest = filtered.value[folderIdx]
  if (!dest || dest.type !== FILE_TYPE.FOLDER) return
  const filesToMove = []
  if (dragIsGrouped.value && checked.value.has(dragFileIdx.value)) {
    ;[...checked.value].forEach(i => {
      const f = filtered.value[i]
      if (f?.type === FILE_TYPE.FILE) filesToMove.push(f)
    })
  } else {
    const f = filtered.value[dragFileIdx.value]
    if (f) filesToMove.push(f)
  }
  dragFileIdx.value = null
  dragIsGrouped.value = false
  if (!filesToMove.length) return
  await _checkAndMove(filesToMove, dest.path)
}

// ─── CONFLICT CHECK BEFORE MOVE ───
export async function _checkAndMove(filesToMove, destPath) {
  try {
    const res = await apiFetch('/api/media/check-move-conflicts', {
      method: 'POST',
      body: JSON.stringify({ file_names: filesToMove.map(f => f.name), dest_folder: destPath }),
    })
    const data = await res.json()
    if (data.conflicts?.length > 0) {
      moveConflicts.value = data.conflicts
      pendingMoveFiles.value = filesToMove
      pendingMoveDest.value = destPath
      showMoveConflictModal.value = true
      return
    }
  } catch {
    /* silent: conflict pre-check skipped, backend will still validate */
  }
  await _execMoveFiles(filesToMove, destPath, false)
}

export async function execMoveWithOverwrite(overwrite) {
  showMoveConflictModal.value = false
  const filesToMove = [...pendingMoveFiles.value]
  const dest = pendingMoveDest.value
  pendingMoveFiles.value = []
  pendingMoveDest.value = ''
  if (!overwrite) {
    const conflictNames = new Set(moveConflicts.value.map(c => c.name))
    const safeFiles = filesToMove.filter(f => !conflictNames.has(f.name))
    moveConflicts.value = []
    if (!safeFiles.length) {
      showToast(_t('mediaManager.moveCancelled'), TOAST_TYPE.WARN)
      return
    }
    await _execMoveFiles(safeFiles, dest, false)
  } else {
    moveConflicts.value = []
    await _execMoveFiles(filesToMove, dest, true)
  }
}

export function cancelMoveConflict() {
  showMoveConflictModal.value = false
  moveConflicts.value = []
  pendingMoveFiles.value = []
  pendingMoveDest.value = ''
}

export async function _execMoveFiles(filesToMove, dest, overwrite) {
  setProgress(5)
  const endpoint = overwrite ? '/api/media/move-overwrite' : '/api/media/move'
  const results = await Promise.allSettled(
    filesToMove.map(f =>
      apiFetch(endpoint, {
        method: 'POST',
        body: JSON.stringify({ src_path: f.path, dest_folder: dest }),
      }).then(r => r.json()),
    ),
  )
  setProgress(95)
  let ok = 0
  const errors = []
  results.forEach((r, i) => {
    if (r.status === 'fulfilled' && !r.value?.error) ok++
    else {
      const errMsg = r.value?.error || r.reason?.message || _t('common.unknownError')
      errors.push(`${filesToMove[i]?.name || '?'} : ${errMsg}`)
    }
  })
  if (ok > 0) _recordMoveHistory(filesToMove, dest, results)
  endProgress()
  if (errors.length === 0) {
    showToast(
      _t('mediaManager.filesMoved', { count: ok }) +
        (overwrite ? ' ' + _t('mediaManager.overwritten') : ''),
      TOAST_TYPE.OK,
    )
  } else {
    errors.forEach(msg => showToast(msg, TOAST_TYPE.ERR, 8000))
    if (ok > 0)
      showToast(_t('mediaManager.partialResult', { ok, errors: errors.length }), TOAST_TYPE.WARN)
  }
  checked.value = new Set()
  loadFiles()
}

function _recordMoveHistory(files, dest, results) {
  const items = []
  files.forEach((f, i) => {
    const r = results[i]
    if (r?.status === 'fulfilled' && !r.value?.error) {
      items.push({ name: f.name, oldPath: f.path, newPath: dest + '/' + f.name })
    }
  })
  if (!items.length) return
  moveHistory.value.unshift({ timestamp: Date.now(), items, dest })
  _saveMoveHistory()
}
