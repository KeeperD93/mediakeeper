import { ref, computed, watch, onScopeDispose } from 'vue'
import { rootZoom } from '@/utils/zoom'

/**
 * Reusable rectangle lasso for selecting items in a scrollable list.
 *
 * Mouse-down on the container (off-row) starts a drag rectangle that
 * follows the cursor and is bounded to the container. Each move emits
 * the indices currently intersecting the rectangle through ``onSelect``.
 * Mouse-up commits, ESC cancels (no ``onSelect`` re-fires after cancel),
 * and a mouse-down on a row or interactive control is ignored so the
 * existing click / Ctrl+click selection paths keep working.
 *
 * Index resolution is delegated to the ``hitTest`` callback so the
 * caller decides how to map the rectangle to ids — keeps the composable
 * agnostic of virtualization, row height, or DOM layout. The rectangle
 * lives in container-document coordinates (``scrollLeft/scrollTop``
 * baked in) so virtualized lists can do pure math.
 *
 * Returns the dragging flag plus a computed style object the template
 * binds to a positioned ``<div>``. A11y note: alternative keyboard
 * selection is intentionally not provided — Ctrl/Shift-clicking rows
 * already covers the multi-select path for keyboard users.
 */
export function useRectLasso({ container, hitTest, onSelect, onCancel, excludeSelector = '' }) {
  const isDragging = ref(false)
  const startX = ref(0)
  const startY = ref(0)
  const curX = ref(0)
  const curY = ref(0)

  const rectStyle = computed(() => {
    if (!isDragging.value) return { display: 'none' }
    const x1 = Math.min(startX.value, curX.value)
    const x2 = Math.max(startX.value, curX.value)
    const y1 = Math.min(startY.value, curY.value)
    const y2 = Math.max(startY.value, curY.value)
    return {
      left: x1 + 'px',
      top: y1 + 'px',
      width: x2 - x1 + 'px',
      height: y2 - y1 + 'px',
    }
  })

  function _toLocal(e) {
    const el = container.value
    const r = el.getBoundingClientRect()
    // Clamp to the container so a fast drag past the edges doesn't
    // produce a rectangle outside the visible scroll area.
    // admin zoom: clientX/Y and getBoundingClientRect agree in unzoomed viewport
    // space; the offset is then scaled into the zoomed container coords the lasso
    // rect and hit-test work in (utils/zoom).
    const z = rootZoom()
    const localX = Math.min(Math.max(e.clientX - r.left, 0), r.width) / z
    const localY = Math.min(Math.max(e.clientY - r.top, 0), r.height) / z
    return {
      x: localX + el.scrollLeft,
      y: localY + el.scrollTop,
    }
  }

  function _emitHit() {
    if (!hitTest || !onSelect) return
    const x1 = Math.min(startX.value, curX.value)
    const x2 = Math.max(startX.value, curX.value)
    const y1 = Math.min(startY.value, curY.value)
    const y2 = Math.max(startY.value, curY.value)
    const ids = hitTest({ x1, y1, x2, y2 }) || []
    onSelect(ids)
  }

  function _onMouseDown(e) {
    if (e.button !== 0) return
    if (excludeSelector && e.target.closest && e.target.closest(excludeSelector)) return
    if (!container.value) return
    const p = _toLocal(e)
    startX.value = p.x
    startY.value = p.y
    curX.value = p.x
    curY.value = p.y
    isDragging.value = true
  }

  function _onMouseMove(e) {
    if (!isDragging.value) return
    const p = _toLocal(e)
    curX.value = p.x
    curY.value = p.y
    _emitHit()
  }

  function _onMouseUp() {
    if (!isDragging.value) return
    isDragging.value = false
  }

  function _onKeyDown(e) {
    if (!isDragging.value || e.key !== 'Escape') return
    isDragging.value = false
    if (onCancel) onCancel()
  }

  function _attach(el) {
    if (!el) return
    el.addEventListener('mousedown', _onMouseDown)
    el.addEventListener('mousemove', _onMouseMove)
    el.addEventListener('mouseup', _onMouseUp)
    el.addEventListener('mouseleave', _onMouseUp)
    document.addEventListener('keydown', _onKeyDown)
  }
  function _detach(el) {
    if (!el) return
    el.removeEventListener('mousedown', _onMouseDown)
    el.removeEventListener('mousemove', _onMouseMove)
    el.removeEventListener('mouseup', _onMouseUp)
    el.removeEventListener('mouseleave', _onMouseUp)
    document.removeEventListener('keydown', _onKeyDown)
  }

  const stopWatch = watch(
    container,
    (el, oldEl) => {
      if (oldEl) _detach(oldEl)
      if (el) _attach(el)
    },
    { immediate: true },
  )

  onScopeDispose(() => {
    stopWatch()
    _detach(container.value)
  })

  return {
    isDragging,
    rectStyle,
    // Exposed for explicit attach scenarios (e.g. tests, custom wiring).
    _onMouseDown,
    _onMouseMove,
    _onMouseUp,
    _onKeyDown,
  }
}
