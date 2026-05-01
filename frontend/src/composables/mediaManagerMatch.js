import * as mmState from './mediaManagerState'
import {
  apiGet, apiFetch, showToast, _t,
  activeCat, subPath, filtered, checked, selectedTmdb, tmdbResults, currentSeason,
  searchType, newNames, anomalyRules,
  savedFiltered, savedChecked, expandedMode,
  moveHistory, _saveMoveHistory,
  extractionRunning, setExtractionCancelled,
  setProgress, endProgress,
} from './mediaManagerState'
import { sanitize, getGenreCategory } from './mediaManagerHelpers'
import { loadFiles, saveTags, checkedFiles, checkedDirs } from './mediaManagerNavigation'
import { pickTMDB } from './mediaManagerTmdb'
import { TOAST_TYPE } from '@/constants/toast'
import { FILE_TYPE } from '@/constants/mediaManager'

// ─── EXPAND CHECKED FOLDERS ───
export async function expandCheckedFolders() {
  const dirs = checkedDirs.value
  if (!dirs.length) return null
  const allFiles = []
  async function listRecursive(sp) {
    try {
      const data = await apiGet(`/api/media/files/${activeCat.value}?subpath=${encodeURIComponent(sp)}`)
      if (!Array.isArray(data)) return
      for (const item of data) {
        if (item.type === FILE_TYPE.FILE) allFiles.push(item)
        else if (item.type === FILE_TYPE.FOLDER) await listRecursive(`${sp}/${item.name}`)
      }
    } catch (e) { console.error('[mediaManagerMatch.listRecursive] failed to expand folder', e) }
  }
  for (const dir of dirs) {
    const sp = subPath.value ? `${subPath.value}/${dir.name}` : dir.name
    await listRecursive(sp)
  }
  if (!allFiles.length) return null
  savedFiltered.value = [...filtered.value]
  savedChecked.value = new Set(checked.value)
  expandedMode.value = true
  filtered.value = allFiles
  checked.value = new Set(allFiles.map((_, i) => i))
  return allFiles
}

// ─── EXTRACTION FICHIERS DE SOUS-DOSSIERS ───
export function cancelExtraction() { setExtractionCancelled(true) }

export async function extractFromSubfolders() {
  const dirs = checkedDirs.value
  if (!dirs.length) { showToast(_t('mediaManager.selectFoldersToExtract'), TOAST_TYPE.ERR); return }
  extractionRunning.value = true
  setExtractionCancelled(false)
  let destPath
  try {
    const rootData = await apiGet(`/api/media/rootpath/${activeCat.value}`)
    if (!rootData?.path) { showToast(_t('mediaManager.rootPathError'), TOAST_TYPE.ERR); extractionRunning.value = false; return }
    destPath = subPath.value ? rootData.path.replace(/\/$/, '') + '/' + subPath.value.replace(/^\//, '') : rootData.path
  } catch { showToast(_t('common.networkError'), TOAST_TYPE.ERR); extractionRunning.value = false; return }

  const filesToMove = []
  async function listRecursive(sp) {
    if (mmState.extractionCancelled) return
    try {
      const data = await apiGet(`/api/media/files/${activeCat.value}?subpath=${encodeURIComponent(sp)}`)
      if (!Array.isArray(data)) return
      for (const item of data) {
        if (mmState.extractionCancelled) return
        if (item.type === FILE_TYPE.FILE) filesToMove.push(item)
        else if (item.type === FILE_TYPE.FOLDER) await listRecursive(`${sp}/${item.name}`)
      }
    } catch { /* silent: skip unreadable subfolder, continue traversal */ }
  }
  setProgress(5)
  for (const dir of dirs) {
    if (mmState.extractionCancelled) break
    const sp = subPath.value ? `${subPath.value}/${dir.name}` : dir.name
    await listRecursive(sp)
  }
  if (mmState.extractionCancelled) {
    endProgress(); extractionRunning.value = false
    showToast(_t('mediaManager.extractionCancelled'), TOAST_TYPE.WARN)
    checked.value = new Set(); loadFiles(); return
  }
  if (!filesToMove.length) {
    endProgress(); extractionRunning.value = false
    showToast(_t('mediaManager.noFilesInSubfolders'), TOAST_TYPE.ERR)
    return
  }
  let ok = 0, errCount = 0
  const movedItems = []
  for (let i = 0; i < filesToMove.length; i++) {
    if (mmState.extractionCancelled) break
    setProgress(5 + 90 * ((i + 1) / filesToMove.length))
    try {
      const res = await apiFetch('/api/media/move', { method: 'POST', body: JSON.stringify({ src_path: filesToMove[i].path, dest_folder: destPath }) })
      const data = await res.json()
      if (data.error) errCount++
      else { ok++; movedItems.push({ name: filesToMove[i].name, oldPath: filesToMove[i].path, newPath: destPath + '/' + filesToMove[i].name }) }
    } catch { errCount++ }
  }
  if (movedItems.length) {
    moveHistory.value.unshift({ timestamp: Date.now(), items: movedItems, dest: destPath })
    _saveMoveHistory()
  }
  endProgress()
  extractionRunning.value = false
  if (mmState.extractionCancelled) showToast(_t('mediaManager.extractionCancelledPartial', { count: ok }), TOAST_TYPE.WARN)
  else if (errCount === 0) showToast(_t('mediaManager.filesExtracted', { count: ok }), TOAST_TYPE.OK)
  else showToast(_t('mediaManager.partialResult', { ok, errors: errCount }), errCount > 0 && ok === 0 ? TOAST_TYPE.ERR : TOAST_TYPE.WARN)
  checked.value = new Set()
  loadFiles()
}

// ─── NAME GENERATION ───
export async function doMatch(addMode = false) {
  if (!selectedTmdb.value) return
  const item = selectedTmdb.value
  const fr = item.title || ''
  const year = item.year || ''
  if (addMode) { await _doMatchFromTMDB(item, fr) } else {
    let matchFiles = null
    if (checkedDirs.value.length > 0) {
      matchFiles = await expandCheckedFolders()
      if (!matchFiles?.length) { showToast(_t('mediaManager.noFilesInSelectedFolders'), TOAST_TYPE.ERR); return }
    } else if (checkedFiles.value.length > 0) {
      matchFiles = checkedFiles.value
    } else {
      filtered.value.forEach((f, i) => { if (f.type === FILE_TYPE.FILE) checked.value.add(i) })
      matchFiles = [...checked.value].sort((a, b) => a - b).map(i => filtered.value[i]).filter(f => f?.type === FILE_TYPE.FILE)
    }
    if (!matchFiles?.length) { showToast(_t('mediaManager.noVideoFilesFound'), TOAST_TYPE.ERR); return }
    newNames.value = []
    await _doMatchFromFiles(item, fr, year, matchFiles)
    const tagsToSave = {}
    newNames.value.forEach(n => { if (n.category) { tagsToSave[n.name] = n.category; if (n.oldName) tagsToSave[n.oldName] = n.category } })
    if (Object.keys(tagsToSave).length) saveTags(tagsToSave)
  }
  if (checked.value.size > 0 && !expandedMode.value) {
    const ckd = filtered.value.filter((f, i) => checked.value.has(i))
    const unkcd = filtered.value.filter((f, i) => !checked.value.has(i))
    filtered.value = [...ckd, ...unkcd]
    checked.value = new Set(ckd.map((f, i) => i))
  }
  const seenPaths = new Set()
  const seenEpKeys = new Set()
  newNames.value = newNames.value.filter(n => {
    if (n.path) { if (seenPaths.has(n.path)) return false; seenPaths.add(n.path); return true }
    const key = n.name.toLowerCase()
    if (seenEpKeys.has(key)) return false
    seenEpKeys.add(key); return true
  })
}

async function _doMatchFromTMDB(item, fr) {
  const lang = anomalyRules.value._tmdbLang || 'fr-FR'
  const langParam = `?language=${encodeURIComponent(lang)}`
  const seasonsToLoad = []
  if (!currentSeason.value) {
    const s = await apiGet(`/api/media/tmdb/tv/${item.id}/seasons${langParam}`)
    seasonsToLoad.push(...(Array.isArray(s) ? s.map(x => x.number) : []))
  } else seasonsToLoad.push(currentSeason.value)
  for (const sNum of seasonsToLoad) {
    const eps = await apiGet(`/api/media/tmdb/tv/${item.id}/season/${sNum}${langParam}`)
    const sn = String(sNum).padStart(2, '0')
    if (!Array.isArray(eps)) continue
    eps.forEach(ep => {
      const en = String(ep.number).padStart(2, '0')
      const name = sanitize(`${fr} - S${sn}E${en} - ${ep.name}.mkv`)
      if (!newNames.value.find(n => n.name === name))
        newNames.value.push({ name, ext: 'mkv', path: '', oldName: '', mismatch: false, mismatchStrong: false, fileSeason: sNum, targetSeason: sNum })
    })
  }
}

async function _doMatchFromFiles(item, fr, year, matchFiles) {
  if (searchType.value === 'movie') {
    for (const f of matchFiles) {
      const ext = f.name.includes('.') ? '.' + f.name.split('.').pop() : ''
      let title = fr, movieYear = year, genreIds = item.genre_ids || []
      if (matchFiles.length > 1) {
        const guessTitle = f.name
          .replace(/\.[^.]+$/, '')
          .replace(/\b(19|20)\d{2}\b.*/, '')
          .replace(/[._]/g, ' ')
          .replace(/\b(seasons?|seasons?|episodes?|episodes?|ep\s*\d+)\b.*/i, '')
          .replace(/\b(FRENCH|MULTi|VOSTFR|BluRay|WEBRip|HDTV|x264|x265|H264|H265|1080p|720p|4K|HDR|PROPER|REPACK|EXTENDED|Complete|Integrale|Complete|Coffret|Collection|Pack)\b.*/i, '')
          .trim()
        try {
          const lang = anomalyRules.value._tmdbLang || 'fr-FR'
          const results = await apiGet(`/api/media/tmdb/search/movie?q=${encodeURIComponent(guessTitle)}&language=${encodeURIComponent(lang)}`)
          if (results?.length) { title = results[0].title; movieYear = results[0].year || ''; genreIds = results[0].genre_ids || [] }
          else title = guessTitle
        } catch { title = guessTitle }
      }
      const gc = getGenreCategory(genreIds)
      const res = await apiFetch('/api/media/build/movie', { method: 'POST', body: JSON.stringify({ title, year: movieYear, ext }) })
      const d = await res.json()
      newNames.value.push({ name: d.name, ext: ext.replace('.', ''), path: f.path, oldName: f.name, category: gc })
    }
    return
  }
  const neededSeasons = new Set()
  matchFiles.forEach(f => {
    const mSE = f.name.match(/[Ss](\d{1,2})[Ee](\d{1,2})/)
    const mXx = f.name.match(/(\d{1,2})x(\d{2})/)
    if (mSE) neededSeasons.add(parseInt(mSE[1]))
    else if (mXx) neededSeasons.add(parseInt(mXx[1]))
  })
  if (neededSeasons.size === 0) neededSeasons.add(currentSeason.value || 1)
  const _lang = anomalyRules.value._tmdbLang || 'fr-FR'
  const allEps = {}
  for (const sNum of neededSeasons) {
    try {
      const data = await apiGet(`/api/media/tmdb/tv/${item.id}/season/${sNum}?language=${encodeURIComponent(_lang)}`)
      allEps[sNum] = Array.isArray(data) ? data : []
    } catch { allEps[sNum] = [] }
  }
  matchFiles.forEach(f => {
    const ext = f.name.includes('.') ? '.' + f.name.split('.').pop() : ''
    let fileSeason = null, fileEpNum = null
    const mSE = f.name.match(/[Ss](\d{1,2})[Ee](\d{1,2})/)
    const mXx = f.name.match(/(\d{1,2})x(\d{2})/)
    const mEp = f.name.match(/[Ee](\d{1,2})/)
    if (mSE) { fileSeason = parseInt(mSE[1]); fileEpNum = parseInt(mSE[2]) }
    else if (mXx) { fileSeason = parseInt(mXx[1]); fileEpNum = parseInt(mXx[2]) }
    else if (mEp) fileEpNum = parseInt(mEp[1])
    const targetSeason = fileSeason || currentSeason.value || parseInt(Object.keys(allEps)[0]) || 1
    const eps = allEps[targetSeason] || Object.values(allEps)[0] || []
    let ep = null
    if (fileEpNum !== null) ep = eps.find(e => e.number === fileEpNum)
    if (!ep) ep = eps[matchFiles.indexOf(f)]
    const epTitle = ep ? ep.name : `Episode ${fileEpNum || matchFiles.indexOf(f) + 1}`
    const epN = ep ? ep.number : (fileEpNum || matchFiles.indexOf(f) + 1)
    const sn = String(targetSeason).padStart(2, '0')
    const en = String(epN).padStart(2, '0')
    const name = sanitize(`${fr} - S${sn}E${en} - ${epTitle}${ext}`)
    const mismatchStrong = fileSeason !== null && fileSeason !== targetSeason
    const epMismatch = !mismatchStrong && fileEpNum !== null && ep && ep.number !== fileEpNum
    newNames.value.push({ name, ext: ext.replace('.', ''), path: f.path, oldName: f.name, mismatch: !mismatchStrong && !ep, mismatchStrong, fileSeason, targetSeason, epMismatch, srcEp: fileEpNum, propEp: epN })
  })
}

export async function dropOnTmdb(tmdbIdx) {
  const item = tmdbResults.value[tmdbIdx]
  if (!item) return
  pickTMDB(tmdbIdx)
  if (item.type === 'tv') await new Promise(r => setTimeout(r, 500))
  doMatch(false)
}
