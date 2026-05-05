import { apiFetch, fileMetaModal, thumbnailCache } from './mediaManagerState'
import { _parseFileName } from './mediaManagerHelpers'
import { FILE_TYPE } from '@/constants/mediaManager'

// ─── FILE METADATA ───
export async function openFileMeta(f) {
  const parsed = f.type === FILE_TYPE.FILE ? _parseFileName(f.name) : null
  fileMetaModal.value = { show: true, file: f, loading: true, data: null, parsed }
  try {
    const res = await apiFetch(`/api/media/metadata?path=${encodeURIComponent(f.path)}`)
    if (!res.ok) {
      console.error('[openFileMeta] HTTP error:', res.status, res.statusText, 'path:', f.path)
      fileMetaModal.value = { ...fileMetaModal.value, loading: false, data: null }
      return
    }
    const data = await res.json()
    if (data.error) {
      console.error('[openFileMeta] API error:', data.error)
      fileMetaModal.value = { ...fileMetaModal.value, loading: false, data: null }
      return
    }
    const merged = { ...data }
    if (parsed?.langues && !merged.langues) merged.langues = parsed.langues
    if (parsed?.sous_titres && !merged.sous_titres) merged.sous_titres = parsed.sous_titres
    if (parsed?.team && !merged.team) merged.team = parsed.team
    if (parsed?.edition && !merged.edition) merged.edition = parsed.edition
    fileMetaModal.value = { ...fileMetaModal.value, loading: false, data: merged }
  } catch (e) {
    console.error('[openFileMeta] Exception:', e)
    fileMetaModal.value = { ...fileMetaModal.value, loading: false, data: null }
  }
}
export function closeFileMeta() {
  fileMetaModal.value = { show: false, file: null, loading: false, data: null, parsed: null }
}

// ─── THUMBNAIL EMBY ───
export async function loadThumbnail(filePath) {
  if (thumbnailCache.value[filePath] !== undefined) return thumbnailCache.value[filePath]
  thumbnailCache.value = { ...thumbnailCache.value, [filePath]: 'loading' }
  try {
    const res = await apiFetch(`/api/emby/thumbnail?path=${encodeURIComponent(filePath)}`)
    if (res?.ok) {
      const data = await res.json()
      const url = data?.url || null
      thumbnailCache.value = { ...thumbnailCache.value, [filePath]: url }
      return url
    }
  } catch {
    /* silent: thumbnail fallback handled below */
  }
  thumbnailCache.value = { ...thumbnailCache.value, [filePath]: null }
  return null
}
