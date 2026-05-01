import { ref, computed, watch, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApi } from '@/composables/useApi'
import { useToast } from '@/composables/useToast'
import { TOAST_TYPE } from '@/constants/toast'
import { FILE_TYPE } from '@/constants/mediaManager'
import { useMediaManager } from '@/composables/useMediaManager'

/**
 * Groups all UI-only state/behaviour that would otherwise bloat
 * MMFileList: lasso-selection rectangle, context menu, inline rename
 * modal, quality-score popup with penalty detection, and hover
 * thumbnail preview.
 *
 * The caller passes the scroll container ref + the visible filtered
 * items ref so the lasso can resolve indices against the current view.
 */
export function useMMFileListUI({ fileListRef, filtered, checked }) {
  const { t } = useI18n()
  const { apiFetch } = useApi()
  const { showToast } = useToast()
  const { loadFiles, applyRenameInPlace, computeQualityScore, openFileMeta, openMoveModal, deleteFile } = useMediaManager()

  // ── Lasso rectangle ──
  const lasso = ref({ active: false, startX: 0, startY: 0, curX: 0, curY: 0, scrollStart: 0 })
  const ROW_H = 36

  const lassoStyle = computed(() => {
    if (!lasso.value.active) return { display: 'none' }
    const l = lasso.value
    const x1 = Math.min(l.startX, l.curX), x2 = Math.max(l.startX, l.curX)
    const y1 = Math.min(l.startY, l.curY), y2 = Math.max(l.startY, l.curY)
    return { left: x1 + 'px', top: y1 + 'px', width: (x2 - x1) + 'px', height: (y2 - y1) + 'px' }
  })

  function onLassoStart(e) {
    if (e.target.closest('.mm-file-row') || e.target.closest('button') || e.target.closest('input')) return
    if (e.button !== 0) return
    const rect = fileListRef.value.getBoundingClientRect()
    lasso.value = {
      active: true,
      startX: e.clientX - rect.left + fileListRef.value.scrollLeft,
      startY: e.clientY - rect.top + fileListRef.value.scrollTop,
      curX: e.clientX - rect.left + fileListRef.value.scrollLeft,
      curY: e.clientY - rect.top + fileListRef.value.scrollTop,
      scrollStart: fileListRef.value.scrollTop,
    }
  }

  function onLassoMove(e) {
    if (!lasso.value.active) return
    const rect = fileListRef.value.getBoundingClientRect()
    lasso.value.curX = e.clientX - rect.left + fileListRef.value.scrollLeft
    lasso.value.curY = e.clientY - rect.top + fileListRef.value.scrollTop
    const l = lasso.value
    const y1 = Math.min(l.startY, l.curY)
    const y2 = Math.max(l.startY, l.curY)
    const firstIdx = Math.max(0, Math.floor(y1 / ROW_H))
    const lastIdx = Math.min(filtered.value.length - 1, Math.floor(y2 / ROW_H))
    if (firstIdx <= lastIdx) {
      const s = new Set()
      for (let i = firstIdx; i <= lastIdx; i++) {
        if (i >= 0 && i < filtered.value.length) s.add(i)
      }
      checked.value = s
    }
  }

  function onLassoEnd() {
    if (!lasso.value.active) return
    lasso.value.active = false
  }

  // ── Hover thumbnail ──
  const hoverThumbnail = ref({ visible: false, url: null, x: 0, y: 0 })
  const { loadThumbnail } = useMediaManager()
  let _thumbTimer = null
  async function onFileHover(f, e) {
    if (f.type !== FILE_TYPE.FILE) return
    clearTimeout(_thumbTimer)
    _thumbTimer = setTimeout(async () => {
      const url = await loadThumbnail(f.path)
      if (url) hoverThumbnail.value = { visible: true, url, x: e.clientX + 16, y: e.clientY + 16 }
    }, 400)
  }
  function onFileHoverEnd() {
    clearTimeout(_thumbTimer)
    hoverThumbnail.value = { ...hoverThumbnail.value, visible: false }
  }

  // ── Context menu + inline rename modal ──
  const ctxMenu = ref({ show: false, x: 0, y: 0, idx: null, file: null })
  const inlineRename = ref({ show: false, file: null, idx: null, value: '' })
  const renameInputRef = ref(null)
  let _ctxCloseHandler = null

  watch(() => inlineRename.value.show, (v) => {
    if (v) nextTick(() => { renameInputRef.value?.focus(); renameInputRef.value?.select() })
  })

  function openCtxMenu(e, idx, f) {
    if (_ctxCloseHandler) { document.removeEventListener('mousedown', _ctxCloseHandler); _ctxCloseHandler = null }
    ctxMenu.value = { show: true, x: e.clientX, y: e.clientY, idx, file: f }
    _ctxCloseHandler = (ev) => {
      if (!ev.target.closest('.mm-ctx-menu')) {
        ctxMenu.value.show = false
        document.removeEventListener('mousedown', _ctxCloseHandler)
        _ctxCloseHandler = null
      }
    }
    setTimeout(() => document.addEventListener('mousedown', _ctxCloseHandler), 0)
  }

  function ctxRename() {
    const f = ctxMenu.value.file
    const idx = ctxMenu.value.idx
    ctxMenu.value.show = false
    inlineRename.value = { show: true, file: f, idx, value: f.name }
  }

  async function submitInlineRename() {
    const { file, value } = inlineRename.value
    const newName = value.trim()
    if (!newName || newName === file.name) { inlineRename.value.show = false; return }
    inlineRename.value.show = false
    try {
      const res = await apiFetch('/api/media/rename', {
        method: 'POST',
        body: JSON.stringify({ old_path: file.path, new_name: newName }),
      })
      const data = await res.json()
      if (data.error) {
        console.error('[useMMFileListUI.submitInlineRename] backend error', data.error)
        showToast(t('common.apiError.unknown', { status: '' }), TOAST_TYPE.ERR)
      }
      else {
        showToast(t('mediaManager.renamed', { name: newName }), TOAST_TYPE.OK)
        applyRenameInPlace(file.path, newName, data.new_path)
        // Resync from disk so a subsequent move/drag picks up the new path
        // even if the in-place update missed an edge case.
        loadFiles()
      }
    } catch { showToast(t('common.networkError'), TOAST_TYPE.ERR) }
  }

  function ctxMove() { ctxMenu.value.show = false; openMoveModal(ctxMenu.value.idx) }
  function ctxInfo() { ctxMenu.value.show = false; if (ctxMenu.value.file) openFileMeta(ctxMenu.value.file) }
  function ctxDelete() { ctxMenu.value.show = false; deleteFile(ctxMenu.value.idx) }

  // ── Quality score popup with penalty breakdown ──
  const qualityPopup = ref({ visible: false, score: 0, penalties: [], x: 0, y: 0 })

  function showQualityPopup(e, f) {
    const score = computeQualityScore(f.name)
    const n = f.name.replace(/\.[^.]+$/, '')
    const penalties = []
    if (!/\b(480p|720p|1080p|2160p|4K|UHD)\b/i.test(f.name)) penalties.push({ points: 20, label: 'Missing resolution' })
    if (!/\b(19|20)\d{2}\b/.test(f.name) && !/[Ss]\d{1,2}[Ee]\d{1,2}|\d{1,2}x\d{2}/.test(n)) penalties.push({ points: 15, label: 'Missing year/episode' })
    if (/[-_.]{3,}/.test(n)) penalties.push({ points: 10, label: 'Triple separators' })
    if (/\s{2,}/.test(n)) penalties.push({ points: 10, label: 'Espaces doubles' })
    if (/_{2,}/.test(n)) penalties.push({ points: 10, label: 'Underscores doubles' })
    if ((n.match(/\./g) || []).length > 3) penalties.push({ points: 15, label: 'Trop de points' })
    if (f.name.length > 180) penalties.push({ points: 10, label: 'Nom trop long' })
    if (!/\b(x264|x265|H\.?264|H\.?265|HEVC|AVC|VP9|AV1)\b/i.test(f.name)) penalties.push({ points: 5, label: 'Missing video codec' })
    if (!/\b(DTS|Atmos|TrueHD|EAC3|AC3|AAC|FLAC|MP3)\b/i.test(f.name)) penalties.push({ points: 5, label: 'Codec audio manquant' })
    let x = e.clientX - 120, y = e.clientY + 16
    if (x < 10) x = 10
    if (y + 180 > window.innerHeight) y = e.clientY - 180
    qualityPopup.value = { visible: true, score, penalties, x, y }
  }
  function hideQualityPopup() { qualityPopup.value = { ...qualityPopup.value, visible: false } }

  return {
    lasso, lassoStyle, onLassoStart, onLassoMove, onLassoEnd,
    hoverThumbnail, onFileHover, onFileHoverEnd,
    ctxMenu, openCtxMenu, ctxRename, ctxMove, ctxInfo, ctxDelete,
    inlineRename, renameInputRef, submitInlineRename,
    qualityPopup, showQualityPopup, hideQualityPopup,
  }
}
