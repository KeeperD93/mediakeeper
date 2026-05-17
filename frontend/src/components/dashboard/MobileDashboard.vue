<template>
  <div class="m-dash" :class="{ 'm-dash--editing': editMode }">
    <MobileDashboardStats
      :hidden="hidden"
      :duplicates-count="duplicatesCount"
      :media-stats="mediaStats"
    />

    <!-- Edit mode → titles only, drag-reorder. -->
    <MobileDashboardReorderList v-if="editMode" :draft-order="draftOrder" @reorder="onReorder" />

    <!-- Normal mode → full widgets in order. -->
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
      <button
        type="button"
        class="m-dash-customize"
        :aria-label="$t('dashboard.customize')"
        @click="enterEditMode"
      >
        <LayoutGrid :size="14" :stroke-width="2.2" aria-hidden="true" />
        {{ $t('dashboard.customize') }}
      </button>
    </div>

    <MobileDashboardEditToolbar v-if="editMode" @cancel="cancelEdit" @confirm="confirmEdit" />
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { LayoutGrid } from 'lucide-vue-next'
import MobileDashboardStats from '@/components/dashboard/MobileDashboardStats.vue'
import MobileDashboardWidget from '@/components/dashboard/MobileDashboardWidget.vue'
import MobileDashboardReorderList from '@/components/dashboard/MobileDashboardReorderList.vue'
import MobileDashboardEditToolbar from '@/components/dashboard/MobileDashboardEditToolbar.vue'

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

/* Inline "Customize" trigger sits at the end of the stack so it does
   not crowd the data above. Style matches the desktop ghost CTA. */
.m-dash-customize {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  align-self: center;
  margin-top: 4px;
  padding: 8px 14px;
  min-height: 36px;
  border: 1px solid var(--border-default);
  background: var(--surface-2);
  color: var(--text-primary);
  border-radius: var(--radius-input);
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  cursor: pointer;
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
