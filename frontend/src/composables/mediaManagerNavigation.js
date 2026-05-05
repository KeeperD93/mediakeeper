import { computed } from 'vue'
import {
  apiGet,
  apiFetch,
  showToast,
  _t,
  CATS,
  catsLoaded,
  activeCat,
  subPath,
  files,
  filtered,
  checked,
  loading,
  filterQuery,
  sortMode,
  expandedMode,
  tags,
  selectedTmdb,
  tmdbResults,
  showSeasonPanel,
  newNames,
  multiCatMode,
  namingIssues,
  analysisActive,
  newFileThresholdMs,
  _autoSearchState,
} from './mediaManagerState'
import { TOAST_TYPE } from '@/constants/toast'
import { FILE_TYPE } from '@/constants/mediaManager'
import { useConfirm } from '@/composables/useConfirm'

const mkConfirm = useConfirm()

// ─── CATEGORIES ───
export async function loadCategories() {
  try {
    const data = await apiGet('/api/media/categories')
    if (Array.isArray(data) && data.length) {
      CATS.value = data
      catsLoaded.value = true
      if (!data.some(c => c.key === activeCat.value)) activeCat.value = data[0].key
    }
  } catch {
    /* silent: categories fallback to existing state */
  }
}
export async function addCategory(label, path) {
  try {
    const res = await apiFetch('/api/media/categories', {
      method: 'POST',
      body: JSON.stringify({ label, path }),
    })
    const data = await res.json()
    if (data.error) {
      console.error('[mediaManagerNavigation.addCategory] backend error', data.error)
      showToast(_t('common.apiError.unknown', { status: '' }), TOAST_TYPE.ERR)
      return false
    }
    if (data.categories) CATS.value = data.categories
    return true
  } catch {
    showToast(_t('common.networkError'), TOAST_TYPE.ERR)
    return false
  }
}
export async function removeCategory(key) {
  try {
    const res = await apiFetch(`/api/media/categories/${key}`, { method: 'DELETE' })
    const data = await res.json()
    if (data.error) {
      console.error('[mediaManagerNavigation.removeCategory] backend error', data.error)
      showToast(_t('common.apiError.unknown', { status: '' }), TOAST_TYPE.ERR)
      return false
    }
    if (data.categories) CATS.value = data.categories
    if (activeCat.value === key && CATS.value.length) setCat(CATS.value[0].key)
    return true
  } catch {
    showToast(_t('common.networkError'), TOAST_TYPE.ERR)
    return false
  }
}

// ─── COMPUTED ───
export const breadcrumbs = computed(() =>
  subPath.value ? subPath.value.split('/').filter(Boolean) : [],
)
export const fileCount = computed(() => ({
  dirs: filtered.value.filter(f => f.type === FILE_TYPE.FOLDER).length,
  vids: filtered.value.filter(f => f.type === FILE_TYPE.FILE).length,
}))
export const checkedFiles = computed(() =>
  [...checked.value].map(i => filtered.value[i]).filter(f => f?.type === FILE_TYPE.FILE),
)
export const checkedDirs = computed(() =>
  [...checked.value].map(i => filtered.value[i]).filter(f => f?.type === FILE_TYPE.FOLDER),
)
export const hasChecked = computed(() => checked.value.size > 0)
export const newFilesCount = computed(() => {
  const now = Date.now()
  return filtered.value.filter(
    f => f.type === FILE_TYPE.FILE && f.mtime && now - f.mtime * 1000 < newFileThresholdMs,
  ).length
})

// ─── NAVIGATION ───
export function setCat(key) {
  activeCat.value = key
  subPath.value = ''
  checked.value = new Set()
  newNames.value = []
  selectedTmdb.value = null
  tmdbResults.value = []
  showSeasonPanel.value = false
  expandedMode.value = false
  multiCatMode.value = false
  namingIssues.value = {}
  analysisActive.value = false
  loadFiles()
}
export function enterDir(name) {
  subPath.value = subPath.value ? `${subPath.value}/${name}` : name
  checked.value = new Set()
  expandedMode.value = false
  selectedTmdb.value = null
  tmdbResults.value = []
  showSeasonPanel.value = false
  _autoSearchState.dirChangePending = true
  loadFiles()
}
export function navRoot() {
  subPath.value = ''
  checked.value = new Set()
  newNames.value = []
  expandedMode.value = false
  selectedTmdb.value = null
  tmdbResults.value = []
  showSeasonPanel.value = false
  _autoSearchState.dirChangePending = true
  loadFiles()
}
export function navTo(idx) {
  subPath.value = breadcrumbs.value.slice(0, idx + 1).join('/')
  checked.value = new Set()
  expandedMode.value = false
  selectedTmdb.value = null
  tmdbResults.value = []
  showSeasonPanel.value = false
  _autoSearchState.dirChangePending = true
  loadFiles()
}
export function navBack() {
  if (!subPath.value) return
  const parts = subPath.value.split('/').filter(Boolean)
  parts.pop()
  subPath.value = parts.join('/')
  checked.value = new Set()
  expandedMode.value = false
  selectedTmdb.value = null
  tmdbResults.value = []
  showSeasonPanel.value = false
  _autoSearchState.dirChangePending = true
  loadFiles()
}

// ─── CHARGEMENT FICHIERS ───
// Lazy registration for autoSearch to avoid circular deps with tmdb module.
let _autoSearchFn = null
export function _registerAutoSearch(fn) {
  _autoSearchFn = fn
}

export async function loadFiles() {
  loading.value = true
  try {
    const url =
      `/api/media/files/${activeCat.value}` +
      (subPath.value ? `?subpath=${encodeURIComponent(subPath.value)}` : '')
    const data = await apiGet(url)
    if (data && !data.error) {
      files.value = data
      filterQuery.value = ''
      await loadTags()
      applyFilter()
      _autoSearchState.dirChangePending = false
      _autoSearchFn?.()
    } else {
      files.value = []
      filtered.value = []
      _autoSearchState.dirChangePending = false
    }
  } catch {
    files.value = []
    filtered.value = []
    _autoSearchState.dirChangePending = false
  }
  loading.value = false
}

export async function loadTags() {
  try {
    const data = await apiGet('/api/media/tags')
    tags.value = data || {}
  } catch {
    tags.value = {}
  }
}

// Updates a renamed file in place so it keeps its current row.
// A full loadFiles() re-applies the alphabetical sort and pops the
// renamed file to the top whenever its new (cleaner) name compares
// lower than its messy siblings — surprising the user mid-batch.
export function applyRenameInPlace(oldPath, newName, newPath) {
  const now = Date.now() / 1000
  const target = newPath || oldPath.replace(/[^/]+$/, newName)
  const fIdx = files.value.findIndex(f => f.path === oldPath)
  if (fIdx !== -1)
    files.value[fIdx] = { ...files.value[fIdx], name: newName, path: target, mtime: now }
  const ftIdx = filtered.value.findIndex(f => f.path === oldPath)
  if (ftIdx !== -1)
    filtered.value[ftIdx] = { ...filtered.value[ftIdx], name: newName, path: target, mtime: now }
  if (namingIssues.value[oldPath]) {
    const next = { ...namingIssues.value }
    delete next[oldPath]
    namingIssues.value = next
  }
}

export async function saveTags(newTagsObj) {
  try {
    await apiFetch('/api/media/tags', {
      method: 'POST',
      body: JSON.stringify({ tags: newTagsObj }),
    })
    Object.assign(tags.value, newTagsObj)
  } catch (e) {
    console.error('[mediaManagerNavigation.saveTags] failed to save tags', e)
  }
}

export async function toggleMultiCat() {
  if (multiCatMode.value) {
    multiCatMode.value = false
    loadFiles()
    return
  }
  multiCatMode.value = true
  loading.value = true
  try {
    const allFiles = []
    for (const cat of CATS.value) {
      try {
        const data = await apiGet(`/api/media/files/${cat.key}`)
        if (Array.isArray(data))
          data.forEach(f => allFiles.push({ ...f, _cat: cat.key, _catLabel: cat.label }))
      } catch {
        /* silent: per-category fetch error skipped, others still load */
      }
    }
    files.value = allFiles
    filterQuery.value = ''
    applyFilter()
  } catch {
    files.value = []
    filtered.value = []
  }
  loading.value = false
}

// ─── FILTRE / TRI ───
export function applyFilter() {
  let list = [...files.value]
  if (filterQuery.value) {
    const q = filterQuery.value.toLowerCase()
    list = list.filter(f => f.name.toLowerCase().includes(q))
  }
  const dirs = list.filter(f => f.type === FILE_TYPE.FOLDER)
  const fls = list.filter(f => f.type === FILE_TYPE.FILE)
  const cmp = (a, b) => {
    if (analysisActive.value) {
      const aIssue = namingIssues.value[a.path] ? 1 : 0
      const bIssue = namingIssues.value[b.path] ? 1 : 0
      if (aIssue !== bIssue) return bIssue - aIssue
    }
    if (sortMode.value === 'name-asc') return a.name.localeCompare(b.name)
    if (sortMode.value === 'name-desc') return b.name.localeCompare(a.name)
    if (sortMode.value === 'size-asc') return (a.size || 0) - (b.size || 0)
    if (sortMode.value === 'size-desc') return (b.size || 0) - (a.size || 0)
    return 0
  }
  dirs.sort(cmp)
  fls.sort(cmp)
  filtered.value = [...dirs, ...fls]
  checked.value = new Set()
}
export function sortLeft(mode) {
  sortMode.value = mode
  applyFilter()
}

// ─── SELECTION ───
export function toggleCheck(idx) {
  const s = new Set(checked.value)
  if (s.has(idx)) s.delete(idx)
  else s.add(idx)
  checked.value = s
  selectedTmdb.value = null
  tmdbResults.value = []
  showSeasonPanel.value = false
  _autoSearchFn?.()
}
export function toggleAll(val) {
  checked.value = val ? new Set(filtered.value.map((_, i) => i)) : new Set()
  _autoSearchFn?.()
}

// ─── DELETE ───
export async function deleteFile(idx) {
  const f = filtered.value[idx]
  if (!f) return
  const ok = await mkConfirm({
    title: _t('common.confirmTitle.delete'),
    message: _t('mediaManager.confirmDelete', { name: f.name }),
    variant: 'danger',
    confirmLabel: _t('common.delete'),
  })
  if (!ok) return
  try {
    const res = await apiFetch('/api/media/delete', {
      method: 'POST',
      body: JSON.stringify({ path: f.path }),
    })
    const data = await res.json()
    if (data.error) {
      console.error('[mediaManagerNavigation.deleteFile] backend error', data.error)
      showToast(_t('common.apiError.unknown', { status: '' }), TOAST_TYPE.ERR)
    } else {
      showToast(_t('mediaManager.deleted'), TOAST_TYPE.OK)
      loadFiles()
    }
  } catch {
    showToast(_t('common.networkError'), TOAST_TYPE.ERR)
  }
}
export async function deleteSelected() {
  const sel = [...checked.value]
  if (!sel.length) return
  const names = sel.map(i => filtered.value[i]?.name).filter(Boolean)
  const ok = await mkConfirm({
    title: _t('common.confirmTitle.delete'),
    message: _t('mediaManager.confirmDeleteBatch', { count: names.length }),
    variant: 'danger',
    confirmLabel: _t('common.delete'),
  })
  if (!ok) return
  const paths = sel.map(i => filtered.value[i]?.path).filter(Boolean)
  try {
    const res = await apiFetch('/api/media/delete-batch', {
      method: 'POST',
      body: JSON.stringify({ paths }),
    })
    const data = await res.json()
    if (data.errors > 0)
      showToast(
        _t('mediaManager.deletedPartial', { ok: data.deleted, errors: data.errors }),
        TOAST_TYPE.WARN,
      )
    else showToast(_t('mediaManager.deleted'), TOAST_TYPE.OK)
    checked.value = new Set()
    loadFiles()
  } catch {
    showToast(_t('common.networkError'), TOAST_TYPE.ERR)
  }
}

export function getFileCat(f) {
  if (f.type === FILE_TYPE.FOLDER) return null
  return f._category || tags.value[f.name] || null
}

// ─── EMBY ───
export async function refreshEmby() {
  try {
    const res = await apiFetch('/api/emby/refresh', { method: 'POST' })
    const data = await res.json()
    if (data.error) {
      console.error('[mediaManagerNavigation.refreshEmby] backend error', data.error)
      showToast(_t('common.apiError.unknown', { status: '' }), TOAST_TYPE.ERR)
    } else showToast(_t('mediaManager.embyScanStarted'), TOAST_TYPE.OK)
  } catch {
    showToast(_t('common.networkError'), TOAST_TYPE.ERR)
  }
}
