<template>
  <div class="m-dash" :class="{ 'm-dash--editing': editMode }">
    <MobileDashboardStats
      :hidden="hidden"
      :duplicates-count="duplicatesCount"
      :media-stats="mediaStats"
    />

    <TransitionGroup tag="div" name="m-dash-reorder" class="m-dash-stack">
      <MobileDashboardItem
        v-for="id in draftOrder"
        :id="id"
        :key="id"
        :editing="editMode"
        :dragging="draggedId === id"
        :dimmed="draggedId !== null && draggedId !== id"
        :drag-height="draggedId === id ? dragHeight : 0"
        :float-style="draggedId === id ? floatStyle : null"
        :handle-label="$t('dashboard.mobileReorderTitle')"
        @touchstart="onItemTouchStart($event, id)"
        @touchmove="onItemTouchMove"
        @touchend="onItemTouchEnd"
        @touchcancel="onItemTouchEnd"
        @handle-touchstart="onHandleTouchStart($event, id)"
      >
        <MobileDashboardWidget
          :id="id"
          :logs="logs"
          :alerts="alerts"
          :sessions="sessions"
          :seen-alert-ids="seenAlertIds"
          :emby-base-url="embyBaseUrl"
          :watchlist-label="watchlistLabel"
          :watchlist-scan-ago="watchlistScanAgo"
          :leaderboard-entries="leaderboardEntries"
        />
      </MobileDashboardItem>
    </TransitionGroup>

    <MobileDashboardEditToolbar v-if="editMode" @cancel="cancelEdit" @confirm="confirmEdit" />
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import MobileDashboardStats from '@/components/dashboard/MobileDashboardStats.vue'
import MobileDashboardWidget from '@/components/dashboard/MobileDashboardWidget.vue'
import MobileDashboardItem from '@/components/dashboard/MobileDashboardItem.vue'
import MobileDashboardEditToolbar from '@/components/dashboard/MobileDashboardEditToolbar.vue'
import { useLongPress } from '@/composables/useLongPress'

const props = defineProps({
  hidden: { type: Array, default: () => [] },
  order: { type: Array, default: () => [] },
  logs: { type: Array, default: () => [] },
  alerts: { type: Array, default: () => [] },
  sessions: { type: Array, default: () => [] },
  seenAlertIds: { type: Set, default: () => new Set() },
  embyBaseUrl: { type: String, default: '' },
  duplicatesCount: { type: [String, Number], default: '—' },
  watchlistLabel: { type: String, default: '' },
  watchlistScanAgo: { type: String, default: '' },
  mediaStats: {
    type: Object,
    default: () => ({ plays: '—', duration: '—', storage: '—' }),
  },
  leaderboardEntries: { type: Array, default: () => [] },
})

const emit = defineEmits(['update:order'])

const ENTER_LONG_PRESS_MS = 500
const DRAG_LONG_PRESS_MS = 2000
const AUTOSCROLL_ZONE_PX = 80
const AUTOSCROLL_MAX_SPEED = 14

// Local draft so cancel restores the pre-edit ordering. Drag handlers
// mutate ``draftOrder`` so the TransitionGroup animates each swap; the
// parent only learns about the result on Done.
const draftOrder = ref(props.order.slice())
const editMode = ref(false)
const draggedId = ref(null)
let snapshot = []

// Drag geometry captured when the drag is confirmed so the floating
// card stays locked to the finger regardless of the grip point.
const dragHeight = ref(0)
const dragLeft = ref(0)
const dragWidth = ref(0)
let dragOffsetY = 0
let lastTouchY = 0
const floatTop = ref(0)
let autoScrollRAF = null

const floatStyle = computed(() => ({
  position: 'fixed',
  top: floatTop.value + 'px',
  left: dragLeft.value + 'px',
  width: dragWidth.value + 'px',
  zIndex: 9999,
  pointerEvents: 'none',
}))

watch(
  () => props.order,
  next => {
    if (!editMode.value) draftOrder.value = next.slice()
  },
  { deep: true },
)

function enterEditMode() {
  if (editMode.value) return
  snapshot = draftOrder.value.slice()
  editMode.value = true
}

function confirmEdit() {
  stopDrag()
  if (draftOrder.value.join('|') !== snapshot.join('|')) {
    emit('update:order', draftOrder.value.slice())
  }
  editMode.value = false
}

function cancelEdit() {
  stopDrag()
  draftOrder.value = snapshot.slice()
  editMode.value = false
}

// Two distinct long-press timers route the same touch:
//   • Out of edit mode → 500 ms → enter edit (no drag yet).
//   • In edit mode → 2000 ms → engage a drag on the touched card.
// The longer 2 s gate leaves room for quick swipes to scroll the page
// while editing, instead of grabbing every card the finger crosses.
const enterLongPress = useLongPress(() => enterEditMode(), { delay: ENTER_LONG_PRESS_MS })

const dragLongPress = useLongPress(
  e => {
    const card = e.target?.closest?.('[data-mobile-card-id]')
    const id = card?.getAttribute('data-mobile-card-id') || null
    if (!id || !card) return
    startDrag(id, card, e)
  },
  // 30 px tolerates the natural finger jitter of a 2 s static hold —
  // 12 px was strict enough that a slight tremor cancelled the timer.
  { delay: DRAG_LONG_PRESS_MS, moveThreshold: 30 },
)

// Touching the grip handle bypasses both timers; the card lifts on
// the first frame.
function onHandleTouchStart(e, id) {
  if (!editMode.value) return
  const card = e.currentTarget?.closest?.('[data-mobile-card-id]')
  if (!card) return
  startDrag(id, card, e)
}

function onItemTouchStart(e, _id) {
  if (editMode.value) dragLongPress.onTouchStart(e)
  else enterLongPress.onTouchStart(e)
}

function onItemTouchMove(e) {
  if (draggedId.value !== null) return
  if (editMode.value) dragLongPress.onTouchMove(e)
  else enterLongPress.onTouchMove(e)
}

function onItemTouchEnd() {
  if (draggedId.value !== null) return
  if (editMode.value) dragLongPress.onTouchEnd()
  else enterLongPress.onTouchEnd()
}

function startDrag(id, cardEl, e) {
  const rect = cardEl.getBoundingClientRect()
  const t = e.touches && e.touches[0]
  if (!t) return
  dragHeight.value = rect.height
  dragLeft.value = rect.left
  dragWidth.value = rect.width
  dragOffsetY = t.clientY - rect.top
  lastTouchY = t.clientY
  floatTop.value = t.clientY - dragOffsetY
  draggedId.value = id
  if (typeof navigator !== 'undefined' && navigator.vibrate) {
    try {
      navigator.vibrate(20)
    } catch {
      /* haptics blocked — silent fail. */
    }
  }
  document.addEventListener('touchmove', handleDocTouchMove, { passive: false })
  document.addEventListener('touchend', stopDrag, { passive: true })
  document.addEventListener('touchcancel', stopDrag, { passive: true })
  ensureAutoScrollLoop()
}

function stopDrag() {
  if (draggedId.value === null) return
  draggedId.value = null
  document.removeEventListener('touchmove', handleDocTouchMove)
  document.removeEventListener('touchend', stopDrag)
  document.removeEventListener('touchcancel', stopDrag)
  stopAutoScrollLoop()
}

function handleDocTouchMove(e) {
  if (draggedId.value === null) return
  e.preventDefault()
  const t = e.touches && e.touches[0]
  if (!t) return
  lastTouchY = t.clientY
  floatTop.value = t.clientY - dragOffsetY
  const el = document.elementFromPoint(t.clientX, t.clientY)
  if (!el) return
  const card = el.closest('[data-mobile-card-id]')
  if (!card) return
  const overId = card.getAttribute('data-mobile-card-id')
  if (!overId || overId === draggedId.value) return
  const fromIdx = draftOrder.value.indexOf(draggedId.value)
  const toIdx = draftOrder.value.indexOf(overId)
  if (fromIdx < 0 || toIdx < 0) return
  const next = draftOrder.value.slice()
  next.splice(fromIdx, 1)
  next.splice(toIdx, 0, draggedId.value)
  draftOrder.value = next
}

// Single rAF loop runs while a drag is active. Distance between
// ``lastTouchY`` and the 80 px edge bands feeds a speed proportional
// to the finger's depth into the band — gentle near the edge, fast
// against it.
function ensureAutoScrollLoop() {
  if (autoScrollRAF !== null) return
  const tick = () => {
    if (draggedId.value === null) {
      autoScrollRAF = null
      return
    }
    const vh = window.innerHeight
    let dy = 0
    if (lastTouchY < AUTOSCROLL_ZONE_PX) {
      dy = -((AUTOSCROLL_ZONE_PX - lastTouchY) / AUTOSCROLL_ZONE_PX) * AUTOSCROLL_MAX_SPEED
    } else if (lastTouchY > vh - AUTOSCROLL_ZONE_PX) {
      dy = ((lastTouchY - (vh - AUTOSCROLL_ZONE_PX)) / AUTOSCROLL_ZONE_PX) * AUTOSCROLL_MAX_SPEED
    }
    if (dy !== 0) window.scrollBy(0, dy)
    autoScrollRAF = requestAnimationFrame(tick)
  }
  autoScrollRAF = requestAnimationFrame(tick)
}

function stopAutoScrollLoop() {
  if (autoScrollRAF !== null) {
    cancelAnimationFrame(autoScrollRAF)
    autoScrollRAF = null
  }
}

onBeforeUnmount(() => {
  stopDrag()
  stopAutoScrollLoop()
})
</script>

<style scoped>
.m-dash {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 12px 14px calc(60px + env(safe-area-inset-bottom, 0px));
}

/* Leave room at the bottom for the sticky toolbar so the last widget
   stays reachable while reordering. */
.m-dash--editing {
  padding-bottom: calc(120px + env(safe-area-inset-bottom, 0px));
}

.m-dash-stack {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.m-dash-reorder-move {
  transition: transform var(--duration-slow) var(--ease-out);
}

/* Widgets expect a grid parent with height: 100% on desktop. On mobile
   there's no grid cell — give each widget a usable min-height. */
.m-dash :deep(.wg-req),
.m-dash :deep(.wg-eng),
.m-dash :deep(.wg-evt),
.m-dash :deep(.uc),
.m-dash :deep(.hm) {
  min-height: 220px;
}
.m-dash :deep(.wg-health) {
  min-height: 0;
}
.m-dash :deep(.tl-root) {
  min-height: 340px;
}
</style>
