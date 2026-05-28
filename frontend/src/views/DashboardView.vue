<template>
  <div ref="dashRef" class="cinema-dash mk-page-root">
    <canvas ref="particleCanvas" class="dash-particles" aria-hidden="true" />

    <HeroCarousel
      :sessions="sessions"
      :all-sessions="allSessions"
      :emby-base-url="embyBaseUrl"
      :emby-server-id="embyServerId"
      @open-fullscreen="openFullscreen"
    />
    <StatRibbon
      :sys="sys"
      :cpu-history="cpuHistory"
      :ram-history="ramHistory"
      :services="servicesList"
    />

    <!-- Mobile: vertical stack of widgets. Long-press → drag-reorder
         lives inside the component; the desktop grid is untouched. -->
    <MobileDashboard
      v-if="isMobile"
      :hidden="hidden"
      :order="effectiveMobileOrder"
      :logs="logs"
      :alerts="alerts"
      :sessions="sessions"
      :seen-alert-ids="seenAlertIds"
      :emby-base-url="embyBaseUrl"
      :duplicates-count="duplicatesCount"
      :watchlist-label="watchlistLabel"
      :watchlist-scan-ago="watchlistScanAgo"
      :media-stats="mediaStats"
      :leaderboard-entries="leaderboardEntries"
      @update:order="setMobileOrder"
    />

    <!-- Edit bar -->
    <div v-if="!isMobile" class="dash-editbar" :class="{ visible: editing }">
      <div class="editbar-left">
        <LayoutGrid :size="16" />
        <span>{{ $t('dashboard.editMode') }}</span>
      </div>
      <div class="editbar-actions">
        <div class="editbar-toggles">
          <button
            v-for="id in Object.keys(WIDGET_REGISTRY)"
            :key="id"
            class="editbar-chip"
            :class="{ 'chip-hidden': hidden.includes(id) }"
            @click="toggleWidget(id)"
          >
            <component :is="WIDGET_ICONS[id]" class="chip-icon" :size="13" :stroke-width="2" />
            <span class="chip-label">{{ $t(WIDGET_TITLE_KEY[id]) }}</span>
            <span class="chip-toggle">
              <Plus v-if="hidden.includes(id)" :size="12" />
              <X v-else :size="12" />
            </span>
          </button>
        </div>
        <MkButton variant="ghost" @click="resetLayout">
          {{ $t('dashboard.resetLayout') }}
        </MkButton>
        <MkButton variant="primary" @click="editing = false">
          {{ $t('dashboard.done') }}
        </MkButton>
      </div>
    </div>

    <!-- Skeleton -->
    <div v-if="!loaded && !isMobile" class="dash-skeleton">
      <div class="skel-row skel-row-main">
        <div class="skel-block skel-timeline" />
        <div class="skel-col">
          <div class="skel-row"><div v-for="n in 4" :key="n" class="skel-block skel-card" /></div>
          <div class="skel-row">
            <div class="skel-block skel-wide" />
            <div class="skel-block skel-wide" />
          </div>
          <div class="skel-block skel-tall" />
        </div>
      </div>
    </div>

    <!-- Grid (desktop only) -->
    <div v-if="loaded && !isMobile" class="dash-grid-wrap">
      <GridLayout
        v-model:layout="layout"
        :col-num="36"
        :row-height="10"
        :margin="[14, 14]"
        :is-draggable="editing"
        :is-resizable="editing"
        :vertical-compact="false"
        :responsive="false"
        :use-css-transforms="true"
        @layout-updated="onLayoutUpdated"
      >
        <GridItem
          v-for="(item, idx) in layout"
          :key="item.i"
          :i="item.i"
          :x="item.x"
          :y="item.y"
          :w="item.w"
          :h="item.h"
          :min-w="item.minW ?? 2"
          :min-h="item.minH ?? 2"
          :max-h="item.maxH ?? Infinity"
          class="dash-widget"
          :class="{ 'widget-editing': editing }"
          :tabindex="editing ? 0 : -1"
          :data-kb-moving="movingItemId === item.i"
          :aria-grabbed="movingItemId === item.i ? 'true' : null"
          @move="onDragStart(item.i)"
          @moved="onDragEnd(item.i)"
          @keydown="e => handleKeydown(e, item.i)"
        >
          <div class="widget-inner" :style="{ animationDelay: idx * 60 + 'ms' }">
            <component
              :is="WIDGET_ICONS[item.i]"
              v-if="WIDGET_ICONS[item.i] && !STAT_CARDS_WITH_ICON.has(item.i)"
              class="widget-badge-icon"
              :size="14"
              :stroke-width="2"
            />

            <ActivityTimeline
              v-if="item.i === 'activity'"
              :logs="logs"
              :alerts="alerts"
              :sessions="sessions"
              :seen-alert-ids="seenAlertIds"
              :emby-base-url="embyBaseUrl"
            />
            <StatCard
              v-if="item.i === 'statPlays'"
              :label="$t('dashboard.totalPlays')"
              :value="mediaStats.plays"
              route="/stats"
              :icon="Play"
              :accent="STAT_CARD_ACCENT.plays"
              :editing="editing"
            />
            <StatCard
              v-if="item.i === 'statDuration'"
              :label="$t('dashboard.totalDuration')"
              :value="mediaStats.duration"
              :icon="Clock"
              :accent="STAT_CARD_ACCENT.duration"
              :editing="editing"
            />
            <StatCard
              v-if="item.i === 'statDuplicates'"
              :label="$t('dashboard.duplicates')"
              :value="duplicatesCount"
              route="/duplicates"
              :icon="Copy"
              :accent="STAT_CARD_ACCENT.duplicates"
              :color="
                duplicatesCount === '—'
                  ? ''
                  : duplicatesCount === '0'
                    ? STAT_STATE_COLOR.ok
                    : STAT_STATE_COLOR.alert
              "
              :editing="editing"
            />
            <StatCard
              v-if="item.i === 'statStorage'"
              :label="$t('dashboard.storage')"
              :value="mediaStats.storage"
              :icon="HardDrive"
              :accent="STAT_CARD_ACCENT.storage"
              :editing="editing"
            />
            <Heatmap v-if="item.i === 'heatmap'" />
            <LeaderboardCard
              v-if="item.i === 'topUsers'"
              :entries="leaderboardEntries.slice(0, 3)"
              widget
            />
            <StatCard
              v-if="item.i === 'linkWatchlist'"
              :label="$t('watchlist.missingEpisodes')"
              :value="watchlistMissingCount"
              route="/watchlist"
              :icon="ClipboardCheck"
              :accent="STAT_CARD_ACCENT.watchlist"
              :color="
                watchlistMissingCount === '—'
                  ? ''
                  : watchlistMissingCount === 0
                    ? STAT_STATE_COLOR.ok
                    : STAT_STATE_COLOR.alert
              "
              :editing="editing"
            />
            <RequestsActionCard v-if="item.i === 'portalAction'" :editing="editing" />
            <PortalEngagementCard v-if="item.i === 'portalEngagement'" :editing="editing" />
            <PortalUpcomingEventsCard v-if="item.i === 'portalEvents'" :editing="editing" />
            <UpcomingEpisodes v-if="item.i === 'upcoming'" />
            <HealthScore v-if="item.i === 'healthScore'" :editing="editing" />
          </div>
        </GridItem>
      </GridLayout>
      <div
        class="sr-only"
        role="status"
        aria-live="polite"
        aria-atomic="true"
        data-testid="dashboard-kb-live"
      >
        {{ liveAnnouncement }}
      </div>
    </div>

    <NowPlayingFullscreen :visible="npVisible" :session="npSession" @close="npVisible = false" />
  </div>
</template>

<script setup>
defineOptions({ name: 'DashboardView' })
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { GridLayout, GridItem } from 'grid-layout-plus'
import { ClipboardCheck, Clock, Copy, HardDrive, LayoutGrid, Play, Plus, X } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { useTheme } from '@/composables/useTheme'
import {
  useDashboardLayout,
  WIDGET_REGISTRY,
  WIDGET_ICONS,
  WIDGET_TITLE_KEY,
} from '@/composables/useDashboardLayout'
import { useDashboardData } from '@/composables/useDashboardData'
import { useDashboardKeyboardMove } from '@/composables/useDashboardKeyboardMove'
import { useDashboardParticles } from '@/composables/useDashboardParticles'
import { useDashboardPolling } from '@/composables/useDashboardPolling'
import { useMobile } from '@/composables/useMobile'

import MkButton from '@/components/common/MkButton.vue'
import { DASHBOARD_EDIT_EVENT } from '@/constants/dashboardEvents'
import { STAT_CARD_ACCENT, STAT_STATE_COLOR } from '@/constants/dashboardStatColors'
import HeroCarousel from '@/components/dashboard/HeroCarousel.vue'
import StatRibbon from '@/components/dashboard/StatRibbon.vue'
import ActivityTimeline from '@/components/dashboard/ActivityTimeline.vue'
import NowPlayingFullscreen from '@/components/dashboard/NowPlayingFullscreen.vue'
import StatCard from '@/components/dashboard/widgets/StatCard.vue'
import Heatmap from '@/components/dashboard/widgets/Heatmap.vue'
import LeaderboardCard from '@/components/portal/profile/LeaderboardCard.vue'
import RequestsActionCard from '@/components/dashboard/widgets/RequestsActionCard.vue'
import PortalEngagementCard from '@/components/dashboard/widgets/PortalEngagementCard.vue'
import PortalUpcomingEventsCard from '@/components/dashboard/widgets/PortalUpcomingEventsCard.vue'
import UpcomingEpisodes from '@/components/dashboard/UpcomingEpisodes.vue'
import HealthScore from '@/components/dashboard/widgets/HealthScore.vue'
import MobileDashboard from '@/components/dashboard/MobileDashboard.vue'

import '@/assets/styles/dashboard-view.css'

const STAT_CARDS_WITH_ICON = new Set(['statPlays', 'statDuration', 'statDuplicates', 'statStorage'])

const { t } = useI18n()
const { particlesEnabled } = useTheme()
const { isMobile } = useMobile()
const {
  editing,
  hidden,
  layout,
  loaded,
  loadLayout,
  toggleWidget,
  resetLayout,
  onLayoutUpdated,
  effectiveMobileOrder,
  setMobileOrder,
} = useDashboardLayout()

const { movingItemId, liveAnnouncement, handleKeydown } = useDashboardKeyboardMove({
  layout,
  editing,
  colNum: 36,
  onLayoutUpdated,
  t,
})

const {
  sys,
  servicesList,
  embyBaseUrl,
  embyServerId,
  sessions,
  allSessions,
  logs,
  alerts,
  seenAlertIds,
  duplicatesCount,
  watchlistLabel,
  watchlistScanAgo,
  mediaStats,
  leaderboardEntries,
  cpuHistory,
  ramHistory,
  loadSystemStats,
  loadServices,
  loadSessions,
  loadLogs,
  loadSeenAlerts,
  loadAlerts,
  loadDuplicates,
  loadWatchlist,
  loadMediaStats,
  loadLeaderboard,
} = useDashboardData()

/* watchlistLabel ships either "{N} {missing}" (when there are missing
 * episodes) or "Suivi" (zero state). The StatCard widget only wants
 * the leading number — extract it here so the card always shows a
 * clean count. Preserves the "—" loading placeholder. */
const watchlistMissingCount = computed(() => {
  if (watchlistLabel.value === '—') return '—'
  const n = parseInt(watchlistLabel.value, 10)
  return Number.isNaN(n) ? 0 : n
})

// ---- Drag snapshot: prevent other tiles from being displaced ----
let dragSnapshot = null
let draggingId = null

function onDragStart(id) {
  if (draggingId) return
  draggingId = id
  dragSnapshot = {}
  for (const item of layout.value) {
    if (item.i !== id) {
      dragSnapshot[item.i] = { x: item.x, y: item.y, w: item.w, h: item.h }
    }
  }
}

function onDragEnd(id) {
  if (dragSnapshot) {
    for (const item of layout.value) {
      if (item.i !== id && dragSnapshot[item.i]) {
        const snap = dragSnapshot[item.i]
        item.x = snap.x
        item.y = snap.y
        item.w = snap.w
        item.h = snap.h
      }
    }
  }
  dragSnapshot = null
  draggingId = null
}

// ---- Particles + polling (extracted composables) ----
const dashRef = ref(null)
const particleCanvas = ref(null)
useDashboardParticles(dashRef, particleCanvas, particlesEnabled)

const { start: startPolling } = useDashboardPolling({
  loadSeenAlerts,
  loadSystemStats,
  loadServices,
  loadSessions,
  loadLogs,
  loadAlerts,
  loadDuplicates,
  loadWatchlist,
  loadMediaStats,
  loadLeaderboard,
})

// ---- NowPlaying fullscreen ----
const npVisible = ref(false)
const npSession = ref({})

function openFullscreen(session) {
  npSession.value = session
  npVisible.value = true
}

// ---- Edit mode bridge ----
function handleDashboardEdit() {
  // Mobile has its own reorder flow handled by MobileDashboard; here we
  // only open the desktop grid edit mode.
  if (isMobile.value) return
  editing.value = true
}

onMounted(async () => {
  await loadLayout()
  await startPolling()
  window.addEventListener(DASHBOARD_EDIT_EVENT, handleDashboardEdit)
})

onUnmounted(() => {
  window.removeEventListener(DASHBOARD_EDIT_EVENT, handleDashboardEdit)
})
</script>
