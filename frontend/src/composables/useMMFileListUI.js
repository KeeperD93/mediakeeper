import { ref, watch, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApi } from '@/composables/useApi'
import { useToast } from '@/composables/useToast'
import { useRectLasso } from '@/composables/useRectLasso'
import { TOAST_TYPE } from '@/constants/toast'
import { useMediaManager } from '@/composables/useMediaManager'
import { rootZoom } from '@/utils/zoom'

/**
 * Groups all UI-only state/behaviour that would otherwise bloat
 * MMFileList: lasso-selection rectangle (delegated to ``useRectLasso``),
 * context menu, inline rename modal, and quality-score popup with
 * penalty detection.
 *
 * The caller passes the scroll container ref + the visible filtered
 * items ref so the lasso can resolve indices against the current view.
 */
export function useMMFileListUI({ fileListRef, filtered, checked }) {
  const { t } = useI18n()
  const { apiFetch } = useApi()
  const { showToast } = useToast()
  const {
    loadFiles,
    applyRenameInPlace,
    computeQualityScore,
    openFileMeta,
    openMoveModal,
    deleteFile,
  } = useMediaManager()

  // ── Lasso rectangle ──
  // Rows are uniform-height, so the lasso resolves selection through
  // ROW_H math instead of querying individual row rects — that keeps
  // virtualized (off-screen) rows reachable too.
  const ROW_H = 36
  const _selectionBeforeLasso = ref(null)

  const { isDragging: lassoDragging, rectStyle: lassoStyle } = useRectLasso({
    container: fileListRef,
    excludeSelector: '.mm-file-row, button, input',
    hitTest: ({ y1, y2 }) => {
      if (_selectionBeforeLasso.value === null) {
        _selectionBeforeLasso.value = new Set(checked.value)
      }
      const total = filtered.value.length
      if (!total) return []
      // Container has gutter padding (design tokens) that offsets the
      // first row's top by ``paddingTop`` — subtract it before mapping
      // y → row index, otherwise the lasso is one row off near the
      // bottom of every drag.
      const el = fileListRef.value
      const padTop = el ? parseFloat(getComputedStyle(el).paddingTop) || 0 : 0
      const adjY1 = Math.max(0, y1 - padTop)
      const adjY2 = Math.max(0, y2 - padTop)
      const firstIdx = Math.max(0, Math.floor(adjY1 / ROW_H))
      const lastIdx = Math.min(total - 1, Math.floor(adjY2 / ROW_H))
      const ids = []
      for (let i = firstIdx; i <= lastIdx; i++) ids.push(i)
      return ids
    },
    onSelect: ids => {
      checked.value = new Set(ids)
    },
    onCancel: () => {
      // ESC → restore the selection that was active before the drag.
      if (_selectionBeforeLasso.value) checked.value = new Set(_selectionBeforeLasso.value)
      _selectionBeforeLasso.value = null
    },
  })

  // Reset the pre-lasso snapshot once the drag finishes normally.
  watch(lassoDragging, dragging => {
    if (!dragging) _selectionBeforeLasso.value = null
  })

  // ── Context menu + inline rename modal ──
  const ctxMenu = ref({ show: false, x: 0, y: 0, idx: null, file: null })
  const inlineRename = ref({ show: false, file: null, idx: null, value: '' })
  const renameInputRef = ref(null)
  let _ctxCloseHandler = null

  watch(
    () => inlineRename.value.show,
    v => {
      if (v)
        nextTick(() => {
          renameInputRef.value?.focus()
          renameInputRef.value?.select()
        })
    },
  )

  function openCtxMenu(e, idx, f) {
    if (_ctxCloseHandler) {
      document.removeEventListener('mousedown', _ctxCloseHandler)
      _ctxCloseHandler = null
    }
    // admin zoom: divide the final position by the factor (utils/zoom).
    const z = rootZoom()
    ctxMenu.value = { show: true, x: e.clientX / z, y: e.clientY / z, idx, file: f }
    _ctxCloseHandler = ev => {
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
    if (!newName || newName === file.name) {
      inlineRename.value.show = false
      return
    }
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
      } else {
        showToast(t('mediaManager.renamed', { name: newName }), TOAST_TYPE.OK)
        applyRenameInPlace(file.path, newName, data.new_path)
        // Resync from disk so a subsequent move/drag picks up the new path
        // even if the in-place update missed an edge case.
        loadFiles()
      }
    } catch {
      showToast(t('common.networkError'), TOAST_TYPE.ERR)
    }
  }

  function ctxMove() {
    ctxMenu.value.show = false
    openMoveModal(ctxMenu.value.idx)
  }
  function ctxInfo() {
    ctxMenu.value.show = false
    if (ctxMenu.value.file) openFileMeta(ctxMenu.value.file)
  }
  function ctxDelete() {
    ctxMenu.value.show = false
    deleteFile(ctxMenu.value.idx)
  }

  // ── Quality score popup with penalty breakdown ──
  const qualityPopup = ref({ visible: false, score: 0, penalties: [], x: 0, y: 0 })

  function showQualityPopup(e, f) {
    const score = computeQualityScore(f.name)
    const n = f.name.replace(/\.[^.]+$/, '')
    const penalties = []
    if (!/\b(480p|720p|1080p|2160p|4K|UHD)\b/i.test(f.name))
      penalties.push({ points: 20, label: 'Missing resolution' })
    if (!/\b(19|20)\d{2}\b/.test(f.name) && !/[Ss]\d{1,2}[Ee]\d{1,2}|\d{1,2}x\d{2}/.test(n))
      penalties.push({ points: 15, label: 'Missing year/episode' })
    if (/[-_.]{3,}/.test(n)) penalties.push({ points: 10, label: 'Triple separators' })
    if (/\s{2,}/.test(n)) penalties.push({ points: 10, label: 'Espaces doubles' })
    if (/_{2,}/.test(n)) penalties.push({ points: 10, label: 'Underscores doubles' })
    if ((n.match(/\./g) || []).length > 3) penalties.push({ points: 15, label: 'Trop de points' })
    if (f.name.length > 180) penalties.push({ points: 10, label: 'Nom trop long' })
    if (!/\b(x264|x265|H\.?264|H\.?265|HEVC|AVC|VP9|AV1)\b/i.test(f.name))
      penalties.push({ points: 5, label: 'Missing video codec' })
    if (!/\b(DTS|Atmos|TrueHD|EAC3|AC3|AAC|FLAC|MP3)\b/i.test(f.name))
      penalties.push({ points: 5, label: 'Codec audio manquant' })
    // admin zoom: clamp in viewport space, then divide the final position by
    // the factor (utils/zoom).
    const z = rootZoom()
    let x = e.clientX - 120,
      y = e.clientY + 16
    if (x < 10) x = 10
    if (y + 180 > window.innerHeight) y = e.clientY - 180
    qualityPopup.value = { visible: true, score, penalties, x: x / z, y: y / z }
  }
  function hideQualityPopup() {
    qualityPopup.value = { ...qualityPopup.value, visible: false }
  }

  return {
    lassoDragging,
    lassoStyle,
    ctxMenu,
    openCtxMenu,
    ctxRename,
    ctxMove,
    ctxInfo,
    ctxDelete,
    inlineRename,
    renameInputRef,
    submitInlineRename,
    qualityPopup,
    showQualityPopup,
    hideQualityPopup,
  }
}
