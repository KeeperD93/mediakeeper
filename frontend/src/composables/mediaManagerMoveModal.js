import { computed } from 'vue'
import {
  apiGet,
  apiFetch,
  showToast,
  _t,
  CATS,
  activeCat,
  subPath,
  filtered,
  modalMoveSrc,
  modalMoveShow,
  moveCat,
  movePath,
  moveFolders,
  moveSearchQ,
  moveSelectedPath,
  moveLoading,
  moveManualPath,
  dragFileIdx,
  moveHistory,
  _saveMoveHistory,
  modalRenameFolderShow,
  renameFolderCurrent,
  renameFolderValue,
  setProgress,
  endProgress,
} from './mediaManagerState'
import { loadFiles, checkedFiles } from './mediaManagerNavigation'
import { _checkAndMove } from './mediaManagerMove'
import { sanitize } from './mediaManagerHelpers'
import { TOAST_TYPE } from '@/constants/toast'
import { FILE_TYPE } from '@/constants/mediaManager'
import { useConfirm } from '@/composables/useConfirm'

const mkConfirm = useConfirm()

// Nom du dossier parent du fichier/dossier en cours de déplacement.
// Sert à suggérer un dossier homonyme au niveau de la cat de destination.
export const suggestedParentName = computed(() => {
  let f = null
  if (modalMoveSrc.value === 'multi') f = checkedFiles.value[0]
  else if (dragFileIdx.value !== null) f = filtered.value[dragFileIdx.value]
  if (!f?.path) return ''
  const segs = f.path.split('/').filter(Boolean)
  return segs.length >= 2 ? segs[segs.length - 2] : ''
})

function _stripYear(name) {
  return name.replace(/\s*\(\d{4}\)\s*$/, '').trim()
}

// Dossier visible au niveau courant qui matche le parent du fichier
// source. Stratégie mixte : on tente d'abord un match exact (nom +
// année comme « Urgences (1994) »). Si rien, on retombe sur un match
// approximatif où l'année « (YYYY) » est ignorée des deux côtés —
// signalé par `exact: false` pour l'UI.
export const suggestedMoveFolder = computed(() => {
  const name = suggestedParentName.value
  if (!name) return null
  const norm = name.toLowerCase()
  const exact = moveFolders.value.find(f => f.name.toLowerCase() === norm)
  if (exact) return { folder: exact, exact: true }
  const baseSrc = _stripYear(name).toLowerCase()
  if (!baseSrc) return null
  const approx = moveFolders.value.find(f => _stripYear(f.name).toLowerCase() === baseSrc)
  return approx ? { folder: approx, exact: false } : null
})

export const moveFoldersFiltered = computed(() => {
  const suggestedPath = suggestedMoveFolder.value?.folder?.path || null
  let list = moveFolders.value
  if (suggestedPath) list = list.filter(f => f.path !== suggestedPath)
  if (!moveSearchQ.value) return list
  const q = moveSearchQ.value.toLowerCase()
  return list.filter(f => f.name.toLowerCase().includes(q))
})
export const moveBreadcrumbs = computed(() =>
  movePath.value ? movePath.value.split('/').filter(Boolean) : [],
)
export const canMoveMulti = computed(() => checkedFiles.value.length > 0)

export function openMoveModal(idx) {
  modalMoveSrc.value = 'single'
  dragFileIdx.value = idx
  _openMoveCommon()
}
export function openMoveModalMulti() {
  modalMoveSrc.value = 'multi'
  _openMoveCommon()
}

async function _openMoveCommon() {
  moveCat.value = activeCat.value
  movePath.value = ''
  moveSelectedPath.value = null
  moveSearchQ.value = ''
  moveManualPath.value = ''
  modalMoveShow.value = true
  await _loadMoveFolders()
}

// Aperçu du chemin absolu de destination (utilisé en bas de la modale).
// Si rien n'est sélectionné, on retombe sur le path courant de la
// catégorie active afin que l'utilisateur voie où il atterrira.
export const moveTargetPreview = computed(() => moveSelectedPath.value || '')

// Nombre de fichiers à déplacer pour cette ouverture de modale.
// Sert à afficher un chip d'indication dans le header.
export const moveSourcesCount = computed(() => {
  if (modalMoveSrc.value === 'multi') return checkedFiles.value.length
  return dragFileIdx.value !== null ? 1 : 0
})

// Destinations utilisées récemment (max 5, dédupliquées). Affichées en
// tête de liste pour accélérer les déplacements répétés.
export const recentMoveDestinations = computed(() => {
  const seen = new Set()
  const out = []
  for (const entry of moveHistory.value) {
    if (!entry?.dest || seen.has(entry.dest)) continue
    seen.add(entry.dest)
    out.push(entry.dest)
    if (out.length >= 5) break
  }
  return out
})

// Bascule la modale sur la cat + le sous-chemin correspondant à un
// chemin absolu (recent ou saisie manuelle). Si le path n'appartient à
// aucune catégorie connue, on le sélectionne tel quel.
export async function jumpToAbsolutePath(absPath) {
  if (!absPath) return
  const trimmed = absPath.replace(/\/+$/, '')
  for (const cat of CATS.value) {
    if (!cat.path) continue
    const root = cat.path.replace(/\/+$/, '')
    if (trimmed === root) {
      moveCat.value = cat.key
      movePath.value = ''
      moveSelectedPath.value = trimmed
      moveSearchQ.value = ''
      await _loadMoveFolders()
      return
    }
    if (trimmed.startsWith(root + '/')) {
      moveCat.value = cat.key
      movePath.value = trimmed.slice(root.length + 1)
      moveSelectedPath.value = trimmed
      moveSearchQ.value = ''
      await _loadMoveFolders()
      return
    }
  }
  // Pas de catégorie correspondante — on accepte tel quel.
  moveSelectedPath.value = trimmed
}

// Saisie manuelle d'un chemin absolu : on tente de naviguer dessus
// puis on vide le champ. Toast d'erreur si chemin vide.
export async function applyManualPath() {
  const raw = (moveManualPath.value || '').trim()
  if (!raw) {
    showToast(_t('mediaManager.manualPathEmpty'), TOAST_TYPE.ERR)
    return
  }
  await jumpToAbsolutePath(raw)
  moveManualPath.value = ''
}
async function _loadMoveFolders() {
  moveLoading.value = true
  try {
    const url =
      `/api/media/files/${moveCat.value}` +
      (movePath.value ? `?subpath=${encodeURIComponent(movePath.value)}` : '')
    const data = await apiGet(url)
    moveFolders.value = Array.isArray(data) ? data.filter(f => f.type === FILE_TYPE.FOLDER) : []
  } catch {
    moveFolders.value = []
  }
  moveLoading.value = false
}
export async function moveChangeCat(key) {
  moveCat.value = key
  movePath.value = ''
  moveSelectedPath.value = null
  moveSearchQ.value = ''
  await _loadMoveFolders()
}
export async function moveEnterFolder(path, name) {
  movePath.value = path ? `${path}/${name}` : name
  moveSelectedPath.value = null
  moveSearchQ.value = ''
  await _loadMoveFolders()
}
export async function moveNavTo(idx) {
  movePath.value = moveBreadcrumbs.value.slice(0, idx + 1).join('/')
  moveSelectedPath.value = null
  moveSearchQ.value = ''
  await _loadMoveFolders()
}
export async function moveNavRoot() {
  movePath.value = ''
  moveSelectedPath.value = null
  moveSearchQ.value = ''
  await _loadMoveFolders()
}
export function movePickFolder(pathOrAbsolute, name) {
  if (pathOrAbsolute && pathOrAbsolute.startsWith('/')) moveSelectedPath.value = pathOrAbsolute
  else moveSelectedPath.value = pathOrAbsolute ? `${pathOrAbsolute}/${name}` : name
}
export async function movePickCurrent() {
  if (movePath.value) {
    try {
      const rootData = await apiGet(`/api/media/rootpath/${moveCat.value}`)
      if (rootData?.path) {
        moveSelectedPath.value =
          rootData.path.replace(/\/$/, '') + '/' + movePath.value.replace(/^\//, '')
        return
      }
    } catch {
      /* silent: fallback to movePath below */
    }
    moveSelectedPath.value = movePath.value
  } else {
    try {
      const rootData = await apiGet(`/api/media/rootpath/${moveCat.value}`)
      if (rootData?.path) {
        moveSelectedPath.value = rootData.path
        return
      }
    } catch {
      /* silent: fallback to local CATS.path */
    }
    const cat = CATS.value.find(c => c.key === moveCat.value)
    moveSelectedPath.value = cat?.path ?? ''
  }
}
export function closeMoveModal() {
  modalMoveShow.value = false
  dragFileIdx.value = null
}

// Resolve the absolute path of the folder currently shown in the move modal.
// Reused by the in-modal "create folder" action so the new folder lands at
// the right place regardless of category root.
async function _resolveMoveAbsolutePath() {
  try {
    const rootData = await apiGet(`/api/media/rootpath/${moveCat.value}`)
    if (rootData?.path) {
      const root = rootData.path.replace(/\/$/, '')
      return movePath.value ? `${root}/${movePath.value.replace(/^\//, '')}` : root
    }
  } catch {
    /* silent: fall back to local CATS metadata */
  }
  const cat = CATS.value.find(c => c.key === moveCat.value)
  const root = (cat?.path ?? '').replace(/\/$/, '')
  if (!root) return ''
  return movePath.value ? `${root}/${movePath.value.replace(/^\//, '')}` : root
}

// Create a folder at the location currently navigated in the move modal,
// then refresh the listing and auto-select the new folder as destination so
// the user just has to confirm with the footer "Move here" button.
export async function createMoveFolder(rawName) {
  const name = sanitize((rawName || '').trim())
  if (!name) {
    showToast(_t('mediaManager.folderNameRequired'), TOAST_TYPE.ERR)
    return false
  }
  if (moveFolders.value.some(f => f.name.toLowerCase() === name.toLowerCase())) {
    showToast(_t('mediaManager.folderAlreadyExists', { name }), TOAST_TYPE.ERR)
    return false
  }
  const parentPath = await _resolveMoveAbsolutePath()
  if (!parentPath) {
    showToast(_t('common.apiError.unknown', { status: '' }), TOAST_TYPE.ERR)
    return false
  }
  try {
    const res = await apiFetch('/api/media/create-folders', {
      method: 'POST',
      body: JSON.stringify({ folders: [{ parent_path: parentPath, folder_name: name }] }),
    })
    const data = await res.json()
    const entry = data?.results?.[0] || null
    if (!entry || entry.error) {
      console.error('[mediaManagerMoveModal.createMoveFolder] backend error', entry?.error)
      showToast(_t('common.apiError.unknown', { status: '' }), TOAST_TYPE.ERR)
      return false
    }
    if (entry.already_existed) {
      showToast(_t('mediaManager.folderAlreadyExists', { name }), TOAST_TYPE.ERR)
      return false
    }
    await _loadMoveFolders()
    moveSelectedPath.value = entry.path || `${parentPath.replace(/\/$/, '')}/${name}`
    showToast(_t('mediaManager.folderCreated', { name }), TOAST_TYPE.OK)
    return true
  } catch (e) {
    console.error('[mediaManagerMoveModal.createMoveFolder] network error', e)
    showToast(_t('common.networkError'), TOAST_TYPE.ERR)
    return false
  }
}

export async function execMove() {
  const dest = moveSelectedPath.value
  if (!dest) return
  const filesToMove = []
  if (modalMoveSrc.value === 'multi') checkedFiles.value.forEach(f => filesToMove.push(f))
  else if (dragFileIdx.value !== null) {
    const f = filtered.value[dragFileIdx.value]
    if (f) filesToMove.push(f)
  }
  closeMoveModal()
  if (!filesToMove.length) return
  await _checkAndMove(filesToMove, dest)
}

// ─── MOVE HISTORY UNDO ───
export async function undoMove(histIdx) {
  const entry = moveHistory.value[histIdx]
  if (!entry?.items?.length) return
  const confirmed = await mkConfirm({
    title: _t('common.confirmTitle.cancel'),
    message: _t('mediaManager.cancelMoveConfirm', { count: entry.items.length }),
    variant: 'warn',
  })
  if (!confirmed) return
  setProgress(5)
  let ok = 0,
    err = 0
  const results = await Promise.allSettled(
    entry.items.map((item, i) => {
      setProgress(5 + 90 * ((i + 1) / entry.items.length))
      const oldDir = item.oldPath.split('/').slice(0, -1).join('/')
      return apiFetch('/api/media/move', {
        method: 'POST',
        body: JSON.stringify({ src_path: item.newPath, dest_folder: oldDir }),
      }).then(r => r.json())
    }),
  )
  results.forEach(r => {
    if (r.status === 'fulfilled' && !r.value?.error) ok++
    else err++
  })
  endProgress()
  if (ok > 0) {
    moveHistory.value.splice(histIdx, 1)
    _saveMoveHistory()
  }
  showToast(
    err === 0
      ? _t('mediaManager.filesRestored', { count: ok })
      : _t('mediaManager.partialResult', { ok, errors: err }),
    err === 0 ? TOAST_TYPE.OK : TOAST_TYPE.ERR,
  )
  loadFiles()
}
export function clearMoveHistory() {
  moveHistory.value = []
  _saveMoveHistory()
  showToast(_t('mediaManager.historyCleared'), TOAST_TYPE.OK)
}

// ─── RENOMMER DOSSIER (simple) ───
export function openRenameFolderModal() {
  if (!subPath.value) return
  renameFolderCurrent.value = subPath.value.split('/').pop()
  renameFolderValue.value = renameFolderCurrent.value
  modalRenameFolderShow.value = true
}
export async function execRenameFolder() {
  const newName = renameFolderValue.value.trim()
  if (!newName || newName === renameFolderCurrent.value) {
    modalRenameFolderShow.value = false
    return
  }
  modalRenameFolderShow.value = false
  setProgress(40)
  try {
    const res = await apiFetch('/api/media/rename-folder', {
      method: 'POST',
      body: JSON.stringify({ cat: activeCat.value, subpath: subPath.value, new_name: newName }),
    })
    const d = await res.json()
    endProgress()
    if (d.error) {
      console.error('[mediaManagerMoveModal.execRenameFolder] backend error', d.error)
      showToast(_t('common.apiError.unknown', { status: '' }), TOAST_TYPE.ERR)
    } else {
      const parts = subPath.value.split('/')
      parts[parts.length - 1] = newName
      subPath.value = parts.join('/')
      showToast(_t('mediaManager.folderRenamed', { name: newName }), TOAST_TYPE.OK)
    }
    loadFiles()
  } catch {
    endProgress()
    showToast(_t('mediaManager.renameError'), TOAST_TYPE.ERR)
  }
}
