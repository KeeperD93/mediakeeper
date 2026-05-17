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
          'm-dash-item--dragging': draggedId === id,
        }"
        :data-mobile-card-id="id"
        @touchstart="onItemTouchStart($event, id)"
        @touchmove="onItemTouchMove"
        @touchend="onItemTouchEnd"
        @touchcancel="onItemTouchEnd"
      >
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
import { onBeforeUnmount, ref, watch } from 'vue'
import { ClipboardCheck, Play, Clock, Copy, HardDrive } from 'lucide-vue-next'
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

// Local draft so a cancel restores the exact pre-edit ordering — the
// drag handlers mutate ``draftOrder`` directly so the TransitionGroup
// animates each swap, but the parent only learns about the new order
// on "Done".
const draftOrder = ref(props.order.slice())
const editMode = ref(false)
const draggedId = ref(null)
let snapshot = []

watch(
  () => props.order,
  next => {
    if (!editMode.value) draftOrder.value = next.slice()
  },
  { deep: true },
)

function enterEditMode(initialDragId) {
  if (editMode.value) return
  snapshot = draftOrder.value.slice()
  editMode.value = true
  if (initialDragId) startDrag(initialDragId)
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

// ─── Long-press → enter edit mode + grab the touched card ─────────
const longPress = useLongPress(e => {
  // The handler stores the id on the most recent touch via dataset
  // lookup; we re-read it here in case the registry order changed.
  const card = e.target?.closest?.('[data-mobile-card-id]')
  const id = card?.getAttribute('data-mobile-card-id') || null
  if (!id) return
  enterEditMode(id)
})

function onItemTouchStart(e, id) {
  if (editMode.value) {
    // Already in edit mode — touching any card starts a drag instantly,
    // no long-press required.
    startDrag(id)
    return
  }
  longPress.onTouchStart(e)
}

function onItemTouchMove(e) {
  if (editMode.value) return
  longPress.onTouchMove(e)
}

function onItemTouchEnd() {
  if (!editMode.value) longPress.onTouchEnd()
}

// ─── Drag-reorder while in edit mode ──────────────────────────────
function startDrag(id) {
  draggedId.value = id
  document.addEventListener('touchmove', handleDocTouchMove, { passive: false })
  document.addEventListener('touchend', stopDrag, { passive: true })
  document.addEventListener('touchcancel', stopDrag, { passive: true })
}

function stopDrag() {
  if (draggedId.value === null) return
  draggedId.value = null
  document.removeEventListener('touchmove', handleDocTouchMove)
  document.removeEventListener('touchend', stopDrag)
  document.removeEventListener('touchcancel', stopDrag)
}

function handleDocTouchMove(e) {
  if (draggedId.value === null) return
  // Block the page's native vertical scroll so the user can drag the
  // card freely without the viewport sliding out from under their
  // finger. ``passive: false`` was opted into when binding above.
  e.preventDefault()
  const t = e.touches && e.touches[0]
  if (!t) return
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

onBeforeUnmount(stopDrag)
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
  /* Touch-action prevents the browser's native long-press selection /
     callout menu on iOS so our gesture wins cleanly. */
  touch-action: pan-y;
  transition: transform 220ms ease, box-shadow 220ms ease;
}

.m-dash-item--editing {
  animation: m-dash-wiggle 1.4s ease-in-out infinite;
  transform-origin: 50% 50%;
}

.m-dash-item--dragging {
  animation: none;
  transform: scale(1.04);
  box-shadow:
    0 18px 38px rgb(0, 0, 0, 0.45),
    0 0 0 2px var(--accent-400, #6366f1);
  z-index: 10;
  position: relative;
  /* The dragged card must NOT translate with TransitionGroup while the
     finger is on it — only the *other* siblings reflow around it. */
  touch-action: none;
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
  .m-dash-item--editing {
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

<style>
/* Sticky toolbar — teleported to <body> so it overlays the entire
   page (above hero, stats, and any fixed nav). Unscoped because the
   teleport target lives outside the component subtree. The ``m-dash``
   namespace keeps it isolated from the rest of the app. */
.m-dash-toolbar {
  position: fixed;
  left: 12px;
  right: 12px;
  bottom: calc(16px + env(safe-area-inset-bottom, 0px));
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 16px;
  background: rgb(15, 18, 32, 0.94);
  border: 1px solid rgb(255, 255, 255, 0.08);
  border-radius: 14px;
  box-shadow: 0 12px 32px rgb(0, 0, 0, 0.45);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  color: #fff;
  font-size: 14px;
}

.m-dash-toolbar__label {
  font-weight: 600;
  letter-spacing: 0.01em;
}

.m-dash-toolbar__actions {
  display: flex;
  gap: 8px;
}

.m-dash-toolbar__btn {
  appearance: none;
  border: 1px solid rgb(255, 255, 255, 0.16);
  background: rgb(255, 255, 255, 0.06);
  color: #fff;
  border-radius: 10px;
  padding: 10px 14px;
  min-height: 44px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}

.m-dash-toolbar__btn--primary {
  background: var(--accent-500, #6366f1);
  border-color: var(--accent-400, #818cf8);
}
</style>
