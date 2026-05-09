import { ref } from 'vue'

/**
 * Keyboard alternative to the mouse drag-and-drop on dashboard widgets
 * (WCAG 2.2 SC 2.5.7). Only active while `editing` is true; otherwise
 * `handleKeydown` short-circuits and the user's keystrokes pass through.
 *
 * Move flow:
 *   Space / Enter on a focused tile  → enter move mode (origin is saved)
 *   Arrow keys                       → 1-cell step inside the 36-col grid
 *                                      (no upper Y bound: vertical-compact
 *                                      is false, the grid grows downward)
 *   Space / Enter (same tile)        → confirm + persist via callback
 *   Escape                           → restore origin
 *
 * The composable mutates `layout.value[idx]` in place, matching how
 * `grid-layout-plus` consumes its bound layout.
 */
export function useDashboardKeyboardMove({
  layout,
  editing,
  colNum,
  onLayoutUpdated,
  t,
}) {
  const movingItemId = ref(null)
  const liveAnnouncement = ref('')
  let origin = null

  function findIndex(id) {
    return layout.value.findIndex(it => it.i === id)
  }

  function announce(key, params) {
    liveAnnouncement.value = params ? t(key, params) : t(key)
  }

  function enterMove(item) {
    movingItemId.value = item.i
    origin = { x: item.x, y: item.y }
    announce('dashboard.a11y.movingWidget')
  }

  function confirmMove() {
    movingItemId.value = null
    origin = null
    announce('dashboard.a11y.moveConfirmed')
    onLayoutUpdated(layout.value)
  }

  function cancelMove(item) {
    if (origin) {
      item.x = origin.x
      item.y = origin.y
    }
    movingItemId.value = null
    origin = null
    announce('dashboard.a11y.moveCancelled')
  }

  function step(item, dx, dy) {
    const w = item.w
    const nextX = Math.min(Math.max(0, item.x + dx), colNum - w)
    const nextY = Math.max(0, item.y + dy)
    item.x = nextX
    item.y = nextY
    announce('dashboard.a11y.movedTo', { x: nextX, y: nextY })
  }

  function handleKeydown(event, itemId) {
    if (!editing.value) return
    const key = event.key
    const idx = findIndex(itemId)
    if (idx === -1) return
    const item = layout.value[idx]

    if (key === ' ' || key === 'Spacebar' || key === 'Enter') {
      if (movingItemId.value === null) {
        enterMove(item)
      } else if (movingItemId.value === itemId) {
        confirmMove()
      } else {
        return
      }
      event.preventDefault()
      return
    }

    if (movingItemId.value !== itemId) return

    if (key === 'Escape') {
      cancelMove(item)
      event.preventDefault()
      return
    }

    if (key === 'ArrowUp') {
      step(item, 0, -1)
      event.preventDefault()
      return
    }
    if (key === 'ArrowDown') {
      step(item, 0, 1)
      event.preventDefault()
      return
    }
    if (key === 'ArrowLeft') {
      step(item, -1, 0)
      event.preventDefault()
      return
    }
    if (key === 'ArrowRight') {
      step(item, 1, 0)
      event.preventDefault()
    }
  }

  return { movingItemId, liveAnnouncement, handleKeydown }
}
