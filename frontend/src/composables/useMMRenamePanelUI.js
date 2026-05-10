import { ref, watch, nextTick } from 'vue'
import { useRectLasso } from '@/composables/useRectLasso'

/**
 * Lasso + batch-delete wiring for the generated-names panel.
 *
 * Mirrors ``useMMFileListUI`` for the right-hand list, but the panel is
 * not virtualized — diff rows can appear between data rows when diffMode
 * is on — so the hitTest reads each row's real bounding rect rather than
 * doing fixed-row-height math. ``deleteSelected`` is a higher-order
 * function: the caller passes ``removeRight`` so the composable stays
 * decoupled from ``useMediaManager`` and remains mockable in tests.
 */
export function useMMRenamePanelUI({ rightListRef, newNames }) {
  const selectedNew = ref(new Set())
  const _selectionBeforeLasso = ref(null)

  const { isDragging: lassoDragging, rectStyle: lassoStyle } = useRectLasso({
    container: rightListRef,
    excludeSelector: '.mm-new-row, .mm-diff-row, button, input',
    hitTest: ({ y1, y2 }) => {
      if (_selectionBeforeLasso.value === null) {
        _selectionBeforeLasso.value = new Set(selectedNew.value)
      }
      const el = rightListRef.value
      if (!el) return []
      const rows = el.querySelectorAll('.mm-new-row')
      if (!rows.length) return []
      // Rows live in container-document coordinates (lasso bakes
      // ``scrollTop`` in), so anchor row rects to the same origin: each
      // row's offsetTop relative to the container is its top edge in
      // that coordinate space, regardless of current scroll.
      const containerRect = el.getBoundingClientRect()
      const ids = []
      for (let i = 0; i < rows.length; i++) {
        const r = rows[i].getBoundingClientRect()
        const top = r.top - containerRect.top + el.scrollTop
        const bottom = top + r.height
        if (bottom >= y1 && top <= y2) ids.push(i)
      }
      return ids
    },
    onSelect: ids => {
      selectedNew.value = new Set(ids)
    },
    onCancel: () => {
      if (_selectionBeforeLasso.value) {
        selectedNew.value = new Set(_selectionBeforeLasso.value)
      }
      _selectionBeforeLasso.value = null
    },
  })

  watch(lassoDragging, dragging => {
    if (dragging) return
    _selectionBeforeLasso.value = null
    if (selectedNew.value.size > 0) {
      // Move focus to the panel so Delete/Backspace/Esc fire without
      // needing a click first.
      nextTick(() => rightListRef.value?.focus?.())
    }
  })

  // Stale indices after the underlying list shrinks would point at
  // wrong rows (or past the end), so reset when the list empties.
  watch(
    () => newNames.value.length,
    len => {
      if (len === 0 && selectedNew.value.size > 0) {
        selectedNew.value = new Set()
      }
    },
  )

  function deleteSelected(removeRight) {
    if (!selectedNew.value.size || typeof removeRight !== 'function') return
    // Splice descending so earlier removals don't shift the indices of
    // later ones.
    const indices = Array.from(selectedNew.value).sort((a, b) => b - a)
    for (const i of indices) removeRight(i)
    selectedNew.value = new Set()
  }

  function clearSelection() {
    selectedNew.value = new Set()
  }

  return {
    lassoDragging,
    lassoStyle,
    selectedNew,
    deleteSelected,
    clearSelection,
  }
}
