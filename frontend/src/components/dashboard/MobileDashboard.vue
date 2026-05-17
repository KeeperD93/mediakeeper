<template>
  <div class="m-dash" :class="{ 'm-dash--editing': editMode }">
    <!-- Stats — fixed 2×2 grid above the reorderable stack. -->
    <div class="m-dash-stats">
      <StatCard
        v-if="!hidden.includes('statPlays')"
        :label="$t('dashboard.totalPlays')"
        :value="mediaStats.plays"
        route="/stats"
        :icon="Play"
        accent="#6366f1"
      />
      <StatCard
        v-if="!hidden.includes('statDuration')"
        :label="$t('dashboard.totalDuration')"
        :value="mediaStats.duration"
        :icon="Clock"
        accent="#10b981"
      />
      <StatCard
        v-if="!hidden.includes('statDuplicates')"
        :label="$t('dashboard.duplicates')"
        :value="duplicatesCount"
        route="/duplicates"
        :icon="Copy"
        accent="#f43f5e"
        :color="duplicatesCount !== '0' && duplicatesCount !== '—' ? '#f43f5e' : ''"
      />
      <StatCard
        v-if="!hidden.includes('statStorage')"
        :label="$t('dashboard.storage')"
        :value="mediaStats.storage"
        :icon="HardDrive"
        accent="#f59e0b"
      />
    </div>

    <TransitionGroup tag="div" name="m-dash-reorder" class="m-dash-stack">
      <div
        v-for="id in draftOrder"
        :key="id"
        class="m-dash-item"
        :class="{
          'm-dash-item--editing': editMode,
          'm-dash-item--placeholder': draggedId === id,
          'm-dash-item--dimmed': draggedId !== null && draggedId !== id,
        }"
        :style="draggedId === id ? { height: dragHeight + 'px' } : null"
        :data-mobile-card-id="id"
        @touchstart="onItemTouchStart($event, id)"
        @touchmove="onItemTouchMove"
        @touchend="onItemTouchEnd"
        @touchcancel="onItemTouchEnd"
      >
        <div
          class="m-dash-item__inner"
          :class="{ 'm-dash-item__inner--floating': draggedId === id }"
          :style="draggedId === id ? floatStyle : null"
        >
          <button
            v-if="editMode"
            type="button"
            class="m-dash-item__handle"
            :aria-label="$t('dashboard.mobileReorderTitle')"
            @touchstart.stop="onHandleTouchStart($event, id)"
          >
            <GripVertical :size="22" :stroke-width="2.4" aria-hidden="true" />
          </button>
          <HealthScore v-if="id === 'healthScore'" />
          <RequestsActionCard v-else-if="id === 'portalAction'" />
          <PortalEngagementCard v-else-if="id === 'portalEngagement'" />
          <PortalUpcomingEventsCard v-else-if="id === 'portalEvents'" />
          <ActivityTimeline
            v-else-if="id === 'activity'"
            :logs="logs"
            :alerts="alerts"
            :sessions="sessions"
            :seen-alert-ids="seenAlertIds"
            :emby-base-url="embyBaseUrl"
          />
          <UpcomingEpisodes v-else-if="id === 'upcoming'" />
          <LeaderboardCard
            v-else-if="id === 'topUsers'"
            :entries="leaderboardEntries.slice(0, 3)"
            widget
          />
          <Heatmap v-else-if="id === 'heatmap'" />
          <QuickLink
            v-else-if="id === 'linkWatchlist'"
            :title="watchlistLabel"
            :subtitle="
              watchlistScanAgo
                ? $t('dashboard.lastScan') + ' ' + watchlistScanAgo
                : $t('sidebar.watchlist')
            "
            route="/watchlist"
            icon-bg="rgba(139,92,246,0.12)"
          >
            <template #icon><ClipboardCheck class="m-dash-ql-icon" :size="18" /></template>
          </QuickLink>
        </div>
      </div>
    </TransitionGroup>

    <!-- Sticky toolbar shown while the user is reordering. -->
    <Teleport to="body">
      <div v-if="editMode" class="m-dash-toolbar" role="toolbar">
        <span class="m-dash-toolbar__label">{{ $t('dashboard.mobileReorderTitle') }}</span>
        <div class="m-dash-toolbar__actions">
          <button type="button" class="m-dash-toolbar__btn" @click="cancelEdit">
            {{ $t('dashboard.mobileReorderCancel') }}
          </button>
          <button
            type="button"
            class="m-dash-toolbar__btn m-dash-toolbar__btn--primary"
            @click="confirmEdit"
          >
            {{ $t('dashboard.mobileReorderDone') }}
          </button>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { ClipboardCheck, GripVertical, Play, Clock, Copy, HardDrive } from 'lucide-vue-next'
import StatCard from '@/components/dashboard/widgets/StatCard.vue'
import Heatmap from '@/components/dashboard/widgets/Heatmap.vue'
import HealthScore from '@/components/dashboard/widgets/HealthScore.vue'
import LeaderboardCard from '@/components/portal/profile/LeaderboardCard.vue'
import QuickLink from '@/components/dashboard/widgets/QuickLink.vue'
import RequestsActionCard from '@/components/dashboard/widgets/RequestsActionCard.vue'
import PortalEngagementCard from '@/components/dashboard/widgets/PortalEngagementCard.vue'
import PortalUpcomingEventsCard from '@/components/dashboard/widgets/PortalUpcomingEventsCard.vue'
import ActivityTimeline from '@/components/dashboard/ActivityTimeline.vue'
import UpcomingEpisodes from '@/components/dashboard/UpcomingEpisodes.vue'
import { useLongPress } from '@/composables/useLongPress'

import '@/assets/styles/dashboard/mobile-dashboard.css'

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

// Local draft so cancel restores the exact pre-edit ordering — drag
// handlers mutate ``draftOrder`` so the TransitionGroup animates each
// swap; the parent only learns about the result on Done.
const draftOrder = ref(props.order.slice())
const editMode = ref(false)
const draggedId = ref(null)
let snapshot = []

// Drag geometry — captured at the moment the drag is confirmed so the
// floating card stays locked to the finger regardless of the user's
// initial grip point on the card.
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

// ─── Long-press timers ────────────────────────────────────────────
//
// Two distinct timers route the same touch:
//   • Out of edit mode → 500 ms → enter edit mode (no drag yet, the
//     user releases and chooses their target).
//   • In edit mode → 2000 ms → engage a drag on the touched card.
//
// The longer 2 s gate matters: it leaves room for a quick swipe to
// scroll the page vertically while editing, instead of accidentally
// grabbing every card the finger crosses.
const enterLongPress = useLongPress(
  () => {
    enterEditMode()
  },
  { delay: ENTER_LONG_PRESS_MS },
)

const dragLongPress = useLongPress(
  e => {
    const card = e.target?.closest?.('[data-mobile-card-id]')
    const id = card?.getAttribute('data-mobile-card-id') || null
    if (!id || !card) return
    startDrag(id, card, e)
  },
  // 30 px tolerates the natural finger jitter of a 2 s static hold —
  // 12 px was strict enough that a slight tremor cancelled the timer
  // before the user could feel the drag engage.
  { delay: DRAG_LONG_PRESS_MS, moveThreshold: 30 },
)

// Tapping the grip handle bypasses both long-press timers entirely.
// Native scroll stays usable elsewhere on the card, and the handle is
// only rendered in edit mode so no accidental drag is possible while
// browsing the dashboard normally.
function onHandleTouchStart(e, id) {
  if (!editMode.value) return
  const card = e.currentTarget?.closest?.('[data-mobile-card-id]')
  if (!card) return
  startDrag(id, card, e)
}

function onItemTouchStart(e, _id) {
  if (editMode.value) {
    dragLongPress.onTouchStart(e)
  } else {
    enterLongPress.onTouchStart(e)
  }
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

// ─── Drag-reorder ─────────────────────────────────────────────────
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
  // Block the native scroll so the finger can pull the card freely.
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

// ─── Auto-scroll when the finger nears the viewport edges ─────────
//
// A single rAF loop runs while a drag is active. Each frame, the
// distance between ``lastTouchY`` and the top/bottom 80 px band feeds
// a speed proportional to how deep into the band the finger is, so
// users get a gentle scroll near the edge and a fast scroll right
// against it. ``elementFromPoint`` is naturally re-queried on the
// next touchmove so the swap logic still fires once the dragged card
// passes over a new neighbour scrolled into view.
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

/* While editing, leave room at the bottom for the sticky toolbar so
   the last widget stays reachable. */
.m-dash--editing {
  padding-bottom: calc(120px + env(safe-area-inset-bottom, 0px));
}

.m-dash-stats {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.m-dash-stack {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.m-dash-item {
  min-height: 120px;
  /* ``pan-y`` keeps the browser's native vertical scroll usable during
     edit mode — users can swipe through the dashboard without lifting
     a card until the 2 s long-press confirms they actually want to
     drag. */
  touch-action: pan-y;
  /* iOS/Android long-press would otherwise fire the text-selection
     callout before our 500 ms / 2 s timer elapses, hijacking the
     gesture. Disable selection + callout on the card surface so the
     gesture stays clean. */
  user-select: none;
  -webkit-user-select: none;
  -webkit-touch-callout: none;
  transition: opacity 200ms ease;
}

.m-dash-item__inner {
  position: relative;
  transition: transform 220ms ease, box-shadow 220ms ease, opacity 200ms ease;
}

/* Edit-mode drag handle — explicit grip the user can grab to lift a
   card instantly without waiting for the 2 s long-press to register.
   Sized 44×44 to meet the Rules.md §2.6 minimum touch target. */
.m-dash-item__handle {
  position: absolute;
  top: 6px;
  right: 6px;
  z-index: 5;
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgb(99, 102, 241, 0.55);
  background: rgb(15, 18, 32, 0.85);
  color: var(--accent-300, #a5b4fc);
  border-radius: 999px;
  cursor: grab;
  box-shadow: 0 6px 14px rgb(0, 0, 0, 0.35);
  /* Ensure the handle wins the gesture even when the user starts on
     its visible bounds — pan-y on the card surface is irrelevant
     here because we bind touchstart directly with .stop. */
  touch-action: none;
}

.m-dash-item__handle:active {
  cursor: grabbing;
  transform: scale(0.94);
}

.m-dash-item--editing .m-dash-item__inner {
  animation: m-dash-wiggle 1.4s ease-in-out infinite;
  transform-origin: 50% 50%;
}

/* The dragged card's slot becomes a placeholder — same height as the
   captured card so neighbours don't reflow vertically when the inner
   lifts into position: fixed, leaving a clearly visible dashed drop
   target where the card will land if released. */
.m-dash-item--placeholder {
  background: rgb(99, 102, 241, 0.08);
  border: 2px dashed rgb(99, 102, 241, 0.45);
  border-radius: 14px;
}
.m-dash-item--placeholder .m-dash-item__inner {
  visibility: hidden;
}

.m-dash-item--dimmed {
  opacity: 0.55;
}
.m-dash-item--dimmed .m-dash-item__inner {
  animation: none;
}

.m-dash-item__inner--floating {
  animation: none !important;
  transform: scale(1.06) rotate(1.2deg);
  box-shadow:
    0 24px 56px rgb(0, 0, 0, 0.55),
    0 0 0 2px var(--accent-400, #6366f1),
    0 0 32px rgb(99, 102, 241, 0.35);
  border-radius: 14px;
  /* The floating clone must not catch touches — they flow through to
     elementFromPoint so the swap logic can see the neighbour below. */
  pointer-events: none;
}

@keyframes m-dash-wiggle {
  0%,
  100% {
    transform: rotate(-0.4deg);
  }
  50% {
    transform: rotate(0.4deg);
  }
}

@media (prefers-reduced-motion: reduce) {
  .m-dash-item--editing .m-dash-item__inner {
    animation: none;
  }
}

/* FLIP animation for the siblings that swap places. */
.m-dash-reorder-move {
  transition: transform 240ms ease;
}

/* Widgets expect a grid parent with height: 100% on desktop. On mobile
   there's no grid cell — we give each widget a usable min-height so
   their content actually shows. */
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
.m-dash-ql-icon {
  color: #8b5cf6;
}
</style>
