import { onBeforeUnmount } from 'vue'

const DEFAULT_DELAY_MS = 500
const DEFAULT_MOVE_THRESHOLD_PX = 10

/**
 * Long-press gesture for touch devices.
 *
 * Returns the four touch handlers to bind in the template (passive is
 * fine — we don't need preventDefault for the detection itself) plus a
 * ``cancel`` helper that callers can invoke imperatively. The callback
 * fires once the pointer has been held still for ``delay`` ms; moving
 * more than ``moveThreshold`` pixels on either axis aborts.
 */
export function useLongPress(callback, options = {}) {
  const delay = options.delay ?? DEFAULT_DELAY_MS
  const moveThreshold = options.moveThreshold ?? DEFAULT_MOVE_THRESHOLD_PX

  let timer = null
  let startX = 0
  let startY = 0

  function cancel() {
    if (timer !== null) {
      clearTimeout(timer)
      timer = null
    }
  }

  function onTouchStart(e) {
    const t = e.touches && e.touches[0]
    if (!t) return
    cancel()
    startX = t.clientX
    startY = t.clientY
    timer = setTimeout(() => {
      timer = null
      callback(e)
    }, delay)
  }

  function onTouchMove(e) {
    if (timer === null) return
    const t = e.touches && e.touches[0]
    if (!t) return
    if (
      Math.abs(t.clientX - startX) > moveThreshold ||
      Math.abs(t.clientY - startY) > moveThreshold
    ) {
      cancel()
    }
  }

  function onTouchEnd() {
    cancel()
  }

  onBeforeUnmount(cancel)

  return {
    onTouchStart,
    onTouchMove,
    onTouchEnd,
    onTouchCancel: cancel,
    cancel,
  }
}
