<template>
  <div class="m-dash" :class="{ 'm-dash--editing': editMode }">
    <MobileDashboardStats
      :hidden="hidden"
      :duplicates-count="duplicatesCount"
      :media-stats="mediaStats"
    />

    <!-- Edit mode → titles only, drag-reorder. -->
    <MobileDashboardReorderList v-if="editMode" :draft-order="draftOrder" @reorder="onReorder" />

    <!-- Normal mode → full widgets in order. The "Customize" entry
         point lives in the global topbar (icon-only on /dashboard
         mobile) and dispatches MOBILE_EDIT_EVENT on the window. -->
    <div v-else class="m-dash-stack">
      <MobileDashboardWidget
        v-for="id in effectiveOrder"
        :id="id"
        :key="id"
        :logs="logs"
        :alerts="alerts"
        :sessions="sessions"
        :seen-alert-ids="seenAlertIds"
        :emby-base-url="embyBaseUrl"
        :watchlist-label="watchlistLabel"
        :watchlist-scan-ago="watchlistScanAgo"
        :leaderboard-entries="leaderboardEntries"
      />
    </div>

    <MobileDashboardEditToolbar v-if="editMode" @cancel="cancelEdit" @confirm="confirmEdit" />
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import MobileDashboardStats from '@/components/dashboard/MobileDashboardStats.vue'
import MobileDashboardWidget from '@/components/dashboard/MobileDashboardWidget.vue'
import MobileDashboardReorderList from '@/components/dashboard/MobileDashboardReorderList.vue'
import MobileDashboardEditToolbar from '@/components/dashboard/MobileDashboardEditToolbar.vue'
import { MOBILE_EDIT_EVENT } from '@/constants/dashboardEvents'

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

// Out of edit mode, the displayed stack mirrors the parent's effective
// order verbatim. In edit mode we work on a local draft so a cancel
// can restore the snapshot without touching the persisted layout.
const editMode = ref(false)
const draftOrder = ref(props.order.slice())
let snapshot = []

const effectiveOrder = computed(() => props.order)

watch(
  () => props.order,
  next => {
    if (!editMode.value) draftOrder.value = next.slice()
  },
  { deep: true },
)

function enterEditMode() {
  if (editMode.value) return
  snapshot = props.order.slice()
  draftOrder.value = props.order.slice()
  editMode.value = true
}

function cancelEdit() {
  draftOrder.value = snapshot.slice()
  editMode.value = false
}

function confirmEdit() {
  if (draftOrder.value.join('|') !== snapshot.join('|')) {
    emit('update:order', draftOrder.value.slice())
  }
  editMode.value = false
}

function onReorder({ fromIdx, toIdx }) {
  const next = draftOrder.value.slice()
  const [moved] = next.splice(fromIdx, 1)
  next.splice(toIdx, 0, moved)
  draftOrder.value = next
}

// The topbar "Customize" button on mobile fires this window-level
// event because the two components live in separate router subtrees.
onMounted(() => {
  window.addEventListener(MOBILE_EDIT_EVENT, enterEditMode)
})
onBeforeUnmount(() => {
  window.removeEventListener(MOBILE_EDIT_EVENT, enterEditMode)
})
</script>

<style scoped>
.m-dash {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 10px 14px calc(60px + env(safe-area-inset-bottom, 0px));
}

/* Leave room at the bottom for the sticky toolbar so the last row
   stays reachable while reordering. */
.m-dash--editing {
  padding-bottom: calc(120px + env(safe-area-inset-bottom, 0px));
}

.m-dash-stack {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

/* Upcoming Episodes — mobile compactage. The default 140 px posters
   shipped in the desktop widget eat the viewport; shrink to ~108 px
   so the user sees roughly 3.3 cards instead of 2.2, and tighten the
   surrounding paddings + gaps so the card itself is shorter. */
.m-dash :deep(.uc-header) {
  padding: 10px 12px 0;
}
.m-dash :deep(.uc-viewport) {
  padding: 8px 0 10px;
}
.m-dash :deep(.uc-track) {
  gap: 10px;
  padding: 0 12px;
}
.m-dash :deep(.uc-card) {
  width: 108px;
  gap: 6px;
}
.m-dash :deep(.uc-meta) {
  font-size: var(--text-3xs);
}
</style>
