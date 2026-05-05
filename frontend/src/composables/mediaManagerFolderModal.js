import { computed } from 'vue'
import {
  apiFetch,
  showToast,
  _t,
  CATS,
  activeCat,
  subPath,
  files,
  modalFolders,
  folderSeriesName,
  folderAudioTags,
  folderBatchAudioTags,
  folderSeasonTags,
  folderPreview,
  folderExistingDirs,
  selectedTmdb,
  seasons,
  _ALL_AUDIO_TAGS,
  setProgress,
  endProgress,
} from './mediaManagerState'
import { sanitize, detectSeasonNum } from './mediaManagerHelpers'
import { loadFiles } from './mediaManagerNavigation'
import { TOAST_TYPE } from '@/constants/toast'
import { FILE_TYPE } from '@/constants/mediaManager'

export const canFolders = computed(() => !!selectedTmdb.value || !!subPath.value)

function _stripAudioSuffix(name) {
  const re = new RegExp(
    `\\s*\\((?:${_ALL_AUDIO_TAGS.join('|')})(?:\\s+(?:${_ALL_AUDIO_TAGS.join('|')}))*\\)\\s*$`,
    'i',
  )
  return name.replace(re, '').trim()
}

function _applyBatchAudioTagsToAll() {
  const tags = [...folderBatchAudioTags.value]
  const suffix = tags.length ? ` (${tags.join(' ')})` : ''
  folderExistingDirs.value = folderExistingDirs.value.map(d => {
    const base = _stripAudioSuffix(d.newName || d.name)
    return { ...d, newName: base + suffix }
  })
}

export function openFolderModal() {
  const item = selectedTmdb.value
  if (item) {
    folderSeriesName.value = item.year ? `${item.title} (${item.year})` : item.title || ''
    folderSeasonTags.value = seasons.value.map(s => ({ season: s.number, active: true }))
  } else if (subPath.value) {
    folderSeriesName.value = subPath.value.split('/').pop()
    folderSeasonTags.value = []
  } else return
  folderAudioTags.value = new Set()
  folderBatchAudioTags.value = new Set()
  folderExistingDirs.value = files.value
    .filter(f => f.type === FILE_TYPE.FOLDER)
    .map(d => {
      const sNum = detectSeasonNum(d.name)
      return {
        name: d.name,
        path: d.path,
        newName: sNum !== null ? `Saison ${String(sNum).padStart(2, '0')}` : d.name,
      }
    })
  autoDetectFolders()
  updateFolderPreview()
  modalFolders.value.show = true
}

export function toggleBatchAudioTag(tag) {
  const s = new Set(folderBatchAudioTags.value)
  if (s.has(tag)) s.delete(tag)
  else s.add(tag)
  folderBatchAudioTags.value = s
  _applyBatchAudioTagsToAll()
}

export function autoDetectFolders() {
  folderExistingDirs.value = folderExistingDirs.value.map(d => {
    const sNum = detectSeasonNum(d.name)
    return { ...d, newName: sNum !== null ? `Saison ${String(sNum).padStart(2, '0')}` : d.name }
  })
}

export function updateFolderPreview() {
  const name = sanitize(folderSeriesName.value.trim() || 'Series name')
  const audioArr = [...folderAudioTags.value]
  const suf = audioArr.length ? ` (${audioArr.join(' ')})` : ''
  let p = `📁 ${name}\n`
  const active = folderSeasonTags.value.filter(s => s.active)
  active.forEach(s => {
    p += `  └── 📁 Saison ${String(s.season).padStart(2, '0')}${suf}\n`
  })
  if (!active.length) p += '  (renommage du dossier uniquement)'
  folderPreview.value = p
}

export function toggleAudioTag(tag) {
  const s = new Set(folderAudioTags.value)
  if (s.has(tag)) s.delete(tag)
  else s.add(tag)
  folderAudioTags.value = s
  updateFolderPreview()
}

export async function execFolderOrganize() {
  const seriesName = sanitize(folderSeriesName.value.trim())
  if (!seriesName) {
    showToast(_t('mediaManager.seriesNameMissing'), TOAST_TYPE.ERR)
    return
  }
  const audioSuffix = folderAudioTags.value.size ? ` (${[...folderAudioTags.value].join(' ')})` : ''
  const active = folderSeasonTags.value.filter(s => s.active)
  modalFolders.value.show = false
  setProgress(15)
  let catBase = CATS.value.find(c => c.key === activeCat.value)?.path || ''
  if (files.value.length > 0 && files.value[0].path) {
    const firstPath = files.value[0].path
    const depthInPath = subPath.value ? subPath.value.split('/').length : 0
    const parts = firstPath.split('/')
    catBase = parts.slice(0, parts.length - 1 - depthInPath).join('/')
  }
  let actualSeriesPath = subPath.value
    ? `${catBase.split('/').slice(0, -subPath.value.split('/').length).join('/')}/${seriesName}`
    : `${catBase}/${seriesName}`
  if (subPath.value) {
    const currentFolderName = subPath.value.split('/').pop()
    if (currentFolderName !== seriesName) {
      try {
        const rfRes = await apiFetch('/api/media/rename-folder', {
          method: 'POST',
          body: JSON.stringify({
            cat: activeCat.value,
            subpath: subPath.value,
            new_name: seriesName,
          }),
        })
        const rfData = await rfRes.json()
        if (rfData.error) {
          console.error('[mediaManagerFolderModal] backend rename-folder error', rfData.error)
          showToast(_t('common.apiError.unknown', { status: '' }), TOAST_TYPE.ERR)
          endProgress()
          return
        }
        if (rfData.new_path) actualSeriesPath = rfData.new_path
      } catch (e) {
        console.error('[mediaManagerFolderModal] failed to rename folder', e)
        showToast(_t('common.networkError'), TOAST_TYPE.ERR)
        endProgress()
        return
      }
    } else {
      actualSeriesPath = `${catBase}/${subPath.value}`
    }
  }
  setProgress(55)
  if (active.length > 0) {
    await apiFetch('/api/media/create-folders', {
      method: 'POST',
      body: JSON.stringify({
        folders: active.map(s => ({
          parent_path: actualSeriesPath,
          folder_name: `Saison ${String(s.season).padStart(2, '0')}${audioSuffix}`,
        })),
      }),
    })
  }
  endProgress()
  const msg =
    subPath.value && active.length
      ? _t('mediaManager.folderRenamedWithSeasons', { count: active.length })
      : subPath.value
        ? _t('mediaManager.folderRenamedSimple')
        : active.length
          ? _t('mediaManager.seasonsCreated', { count: active.length })
          : _t('mediaManager.done')
  showToast(msg, TOAST_TYPE.OK)
  if (subPath.value) {
    const currentFolderName = subPath.value.split('/').pop()
    if (currentFolderName !== seriesName) {
      subPath.value = subPath.value
        .split('/')
        .slice(0, -1)
        .concat([seriesName])
        .join('/')
        .replace(/^\//, '')
    }
  }
  loadFiles()
}

export async function execRenameAllFolders() {
  const toRename = folderExistingDirs.value.filter(d => d.newName && d.newName !== d.name)
  if (!toRename.length) {
    showToast(_t('mediaManager.noFoldersToRename'), TOAST_TYPE.ERR)
    return
  }
  setProgress(5)
  let catBase = CATS.value.find(c => c.key === activeCat.value)?.path || ''
  if (files.value.length > 0 && files.value[0].path) {
    const firstPath = files.value[0].path
    const depthInPath = subPath.value ? subPath.value.split('/').length : 0
    const parts = firstPath.split('/')
    catBase = parts.slice(0, parts.length - 1 - depthInPath).join('/')
  }
  let ok = 0,
    err = 0,
    merged = 0
  for (let i = 0; i < toRename.length; i++) {
    const { path, newName } = toRename[i]
    setProgress(5 + 90 * ((i + 1) / toRename.length))
    const relPath = path.startsWith(catBase) ? path.slice(catBase.length).replace(/^\//, '') : path
    try {
      const res = await apiFetch('/api/media/rename-folder', {
        method: 'POST',
        body: JSON.stringify({ cat: activeCat.value, subpath: relPath, new_name: newName }),
      })
      const data = await res.json()
      if (data.error) err++
      else {
        ok++
        if (data.merged) merged++
      }
    } catch {
      err++
    }
  }
  endProgress()
  let msg = _t('mediaManager.foldersRenamed', { count: ok })
  if (merged > 0) msg += ' (' + _t('mediaManager.foldersMerged', { count: merged }) + ')'
  if (err > 0) msg += ' · ' + _t('mediaManager.errorsCount', { count: err })
  showToast(msg, err === 0 ? TOAST_TYPE.OK : TOAST_TYPE.ERR)
  folderExistingDirs.value = folderExistingDirs.value.map(d => {
    const renamed = toRename.find(r => r.path === d.path)
    if (renamed)
      return { ...d, name: renamed.newName, path: d.path.replace(/[^/]+$/, renamed.newName) }
    return d
  })
  loadFiles()
}
