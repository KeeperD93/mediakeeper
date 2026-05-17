<template>
  <TransitionGroup tag="div" name="m-dash-row" class="m-dash-reorder">
    <div
      v-for="id in draftOrder"
      :key="id"
      class="m-dash-row"
      :class="{ 'm-dash-row--dragging': draggedId === id }"
      :data-reorder-id="id"
    >
      <span class="m-dash-row__title">{{ titleFor(id) }}</span>
      <button
        type="button"
        class="m-dash-row__handle"
        :aria-label="$t('dashboard.mobileReorderTitle')"
        @touchstart.stop="onHandleTouchStart($event, id)"
      >
        <GripHorizontal :size="22" :stroke-width="2.4" aria-hidden="true" />
      </button>
    </div>
  </TransitionGroup>
</template>

<script setup>
import { onBeforeUnmount, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { GripHorizontal } from 'lucide-vue-next'
import { WIDGET_TITLE_KEY } from '@/composables/useDashboardLayout'

const props = defineProps({
  draftOrder: { type: Array, required: true },
})

const emit = defineEmits(['reorder'])

const { t } = useI18n()
const draggedId = ref(null)
// Cooldown gate: after a swap we ignore touchmoves for this many ms
// to let the FLIP transition settle. ``getBoundingClientRect`` in
// Chromium includes the CSS transform mid-animation, so without this
// guard the midpoint check below would see neighbours hover-flick
// over the finger and oscillate.
const SWAP_COOLDOWN_MS = 100
let lastSwapAt = 0

function titleFor(id) {
  const key = WIDGET_TITLE_KEY[id]
  return key ? t(key) : id
}

function onHandleTouchStart(e, id) {
  if (draggedId.value !== null) return
  draggedId.value = id
  if (typeof navigator !== 'undefined' && navigator.vibrate) {
    try {
      navigator.vibrate(15)
    } catch {
      /* haptics blocked — silent fail. */
    }
  }
  document.addEventListener('touchmove', onDocTouchMove, { passive: false })
  document.addEventListener('touchend', endDrag, { passive: true })
  document.addEventListener('touchcancel', endDrag, { passive: true })
}

function endDrag() {
  if (draggedId.value === null) return
  draggedId.value = null
  document.removeEventListener('touchmove', onDocTouchMove)
  document.removeEventListener('touchend', endDrag)
  document.removeEventListener('touchcancel', endDrag)
}

function onDocTouchMove(e) {
  if (draggedId.value === null) return
  // Block the page's native scroll so the finger stays glued to the
  // dragged row while reorder hit-testing happens.
  e.preventDefault()
  // Cooldown gate (see SWAP_COOLDOWN_MS) — bail out fast, no DOM work.
  if (performance.now() - lastSwapAt < SWAP_COOLDOWN_MS) return
  const t0 = e.touches && e.touches[0]
  if (!t0) return
  const el = document.elementFromPoint(t0.clientX, t0.clientY)
  if (!el) return
  const row = el.closest('[data-reorder-id]')
  if (!row) return
  const overId = row.getAttribute('data-reorder-id')
  if (!overId || overId === draggedId.value) return
  const fromIdx = props.draftOrder.indexOf(draggedId.value)
  const toIdx = props.draftOrder.indexOf(overId)
  if (fromIdx < 0 || toIdx < 0) return

  // Midpoint threshold also prevents oscillation: we only commit the
  // swap once the finger has crossed the target row's vertical
  // midpoint in the direction of travel.
  const rect = row.getBoundingClientRect()
  const midY = rect.top + rect.height / 2
  const isDraggingDown = fromIdx < toIdx
  if (isDraggingDown && t0.clientY < midY) return
  if (!isDraggingDown && t0.clientY > midY) return

  emit('reorder', { fromIdx, toIdx })
  lastSwapAt = performance.now()
}

onBeforeUnmount(endDrag)
</script>

<style scoped>
.m-dash-reorder {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.m-dash-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 0 12px;
  background: var(--surface-2);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-input);
  color: var(--text-primary);
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  min-height: 36px;
  /* The row itself does not receive touch — the handle does. Keep
     pan-y so the user can still scroll the list with a finger off the
     handle. */
  touch-action: pan-y;
  transition:
    transform var(--duration-base) var(--ease-default),
    background var(--duration-base) var(--ease-default),
    border-color var(--duration-base) var(--ease-default),
    box-shadow var(--duration-base) var(--ease-default);
}

.m-dash-row--dragging {
  background: rgb(var(--accent-rgb), 0.18);
  border-color: var(--accent-500);
  transform: scale(1.02);
  /* Composite shadow — multi-layer specific (§3.7 tolerance). */
  box-shadow:
    0 12px 28px rgb(0, 0, 0, 0.45),
    0 0 0 1px rgb(var(--accent-rgb), 0.4);
}

.m-dash-row__title {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.m-dash-row__handle {
  flex-shrink: 0;
  /* Documented exception to Rules.md §2.6 (touch targets ≥ 44 px):
     the reorder handle sits inside a list where a mis-tap is
     trivially undone via Cancel — the cost of an oversized handle
     (rows balloon to 52 px each, 9 of them blow past the mobile
     viewport) outweighs the benefit. 36 px remains comfortable on
     touch and matches the common pattern for in-list reorder grips. */
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 0;
  background: transparent;
  color: var(--accent-300);
  cursor: grab;
  padding: 0;
  /* Lock the gesture to the handle — no native scroll race. */
  touch-action: none;
}

.m-dash-row__handle:active {
  cursor: grabbing;
}

/* FLIP animation between siblings on swap. Kept short (--duration-fast)
   so the cooldown gate in onDocTouchMove (100 ms) lets the next swap
   fire just as the previous one finishes — feels snappy, no lag. */
.m-dash-row-move {
  transition: transform var(--duration-fast) var(--ease-out);
}
</style>
