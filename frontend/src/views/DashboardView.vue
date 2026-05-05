<template>
  <div ref="dashRef" class="cinema-dash mk-page-root">
    <canvas ref="particleCanvas" class="dash-particles" aria-hidden="true" />

    <HeroCarousel
      :sessions="sessions"
      :all-sessions="allSessions"
      :emby-base-url="embyBaseUrl"
      @open-fullscreen="openFullscreen"
    />
    <StatRibbon
      :sys="sys"
      :sessions-count="sessions.length"
      :cpu-history="cpuHistory"
      :ram-history="ramHistory"
      :services="servicesList"
    />

    <!-- Mobile: vertical stack of widgets. No drag-resize — customization
         stays a desktop-only feature. -->
    <MobileDashboard
      v-if="isMobile"
      :hidden="hidden"
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
            v-for="(def, id) in WIDGET_REGISTRY"
            :key="id"
            class="editbar-chip"
            :class="{ 'chip-hidden': hidden.includes(id) }"
            @click="toggleWidget(id)"
          >
            <component :is="WIDGET_ICONS[id]" class="chip-icon" :size="13" :stroke-width="2" />
            <span class="chip-label">{{ def.label }}</span>
            <span class="chip-toggle">
              <Plus v-if="hidden.includes(id)" :size="12" />
              <X v-else :size="12" />
            </span>
          </button>
        </div>
        <button class="editbar-btn editbar-reset" @click="resetLayout">
          <RotateCcw :size="14" />
          {{ $t('dashboard.resetLayout') }}
        </button>
        <button class="editbar-btn editbar-done" @click="editing = false">
          <Check :size="14" />
          {{ $t('dashboard.done') }}
        </button>
      </div>
    </div>

    <div v-if="!editing && loaded && !isMobile" class="dash-customize-wrap">
      <button class="dash-customize-btn" @click="editing = true">
        <LayoutGrid :size="14" />
        {{ $t('dashboard.customize') }}
      </button>
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
          @move="onDragStart(item.i)"
          @moved="onDragEnd(item.i)"
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
              accent="#6366f1"
              :editing="editing"
            />
            <StatCard
              v-if="item.i === 'statDuration'"
              :label="$t('dashboard.totalDuration')"
              :value="mediaStats.duration"
              :icon="Clock"
              accent="#10b981"
              :editing="editing"
            />
            <StatCard
              v-if="item.i === 'statDuplicates'"
              :label="$t('dashboard.duplicates')"
              :value="duplicatesCount"
              route="/duplicates"
              :icon="Copy"
              accent="#f43f5e"
              :color="duplicatesCount !== '0' && duplicatesCount !== '—' ? '#f43f5e' : ''"
              :editing="editing"
            />
            <StatCard
              v-if="item.i === 'statStorage'"
              :label="$t('dashboard.storage')"
              :value="mediaStats.storage"
              :icon="HardDrive"
              accent="#f59e0b"
              :editing="editing"
            />
            <Heatmap v-if="item.i === 'heatmap'" />
            <LeaderboardCard
              v-if="item.i === 'topUsers'"
              :entries="leaderboardEntries.slice(0, 3)"
              widget
            />
            <QuickLink
              v-if="item.i === 'linkWatchlist'"
              :title="watchlistLabel"
              :subtitle="
                watchlistScanAgo
                  ? $t('dashboard.lastScan') + ' ' + watchlistScanAgo
                  : $t('sidebar.watchlist')
              "
              route="/watchlist"
              icon-bg="rgba(139,92,246,0.12)"
              :editing="editing"
            >
              <template #icon><ClipboardCheck class="dash-wl-icon" :size="18" /></template>
            </QuickLink>
            <RequestsActionCard v-if="item.i === 'portalAction'" :editing="editing" />
            <PortalEngagementCard v-if="item.i === 'portalEngagement'" :editing="editing" />
            <PortalUpcomingEventsCard v-if="item.i === 'portalEvents'" :editing="editing" />
            <UpcomingEpisodes v-if="item.i === 'upcoming'" />
            <HealthScore v-if="item.i === 'healthScore'" :editing="editing" />
          </div>
        </GridItem>
      </GridLayout>
    </div>

    <NowPlayingFullscreen :visible="npVisible" :session="npSession" @close="npVisible = false" />
  </div>
</template>

<script setup>
defineOptions({ name: 'DashboardView' })
import { ref, onMounted, onUnmounted, onActivated, onDeactivated, nextTick } from 'vue'
import { GridLayout, GridItem } from 'grid-layout-plus'
import {
  Check,
  ClipboardCheck,
  Clock,
  Copy,
  HardDrive,
  LayoutGrid,
  Play,
  Plus,
  RotateCcw,
  X,
} from 'lucide-vue-next'
import { useTheme } from '@/composables/useTheme'
import { useDashboardLayout, WIDGET_REGISTRY, WIDGET_ICONS } from '@/composables/useDashboardLayout'
import { useDashboardData } from '@/composables/useDashboardData'
import { useMobile } from '@/composables/useMobile'

import HeroCarousel from '@/components/dashboard/HeroCarousel.vue'
import StatRibbon from '@/components/dashboard/StatRibbon.vue'
import ActivityTimeline from '@/components/dashboard/ActivityTimeline.vue'
import NowPlayingFullscreen from '@/components/dashboard/NowPlayingFullscreen.vue'
import StatCard from '@/components/dashboard/widgets/StatCard.vue'
import Heatmap from '@/components/dashboard/widgets/Heatmap.vue'
import LeaderboardCard from '@/components/portal/profile/LeaderboardCard.vue'
import QuickLink from '@/components/dashboard/widgets/QuickLink.vue'
import RequestsActionCard from '@/components/dashboard/widgets/RequestsActionCard.vue'
import PortalEngagementCard from '@/components/dashboard/widgets/PortalEngagementCard.vue'
import PortalUpcomingEventsCard from '@/components/dashboard/widgets/PortalUpcomingEventsCard.vue'
import UpcomingEpisodes from '@/components/dashboard/UpcomingEpisodes.vue'
import HealthScore from '@/components/dashboard/widgets/HealthScore.vue'
import MobileDashboard from '@/components/dashboard/MobileDashboard.vue'

import '@/assets/styles/dashboard-view.css'

const STAT_CARDS_WITH_ICON = new Set(['statPlays', 'statDuration', 'statDuplicates', 'statStorage'])

const { particlesEnabled } = useTheme()
const { isMobile } = useMobile()
const { editing, hidden, layout, loaded, loadLayout, toggleWidget, resetLayout, onLayoutUpdated } =
  useDashboardLayout()

const {
  sys,
  servicesList,
  embyBaseUrl,
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

// ---- Particles ----
const dashRef = ref(null)
const particleCanvas = ref(null)
let particleRaf = null
function initParticles() {
  const canvas = particleCanvas.value
  const container = dashRef.value
  if (!canvas || !container) return
  const ctx = canvas.getContext('2d')
  const COUNT = 50
  const particles = []
  let prevW = 0,
    prevH = 0
  function resize() {
    const newW = container.clientWidth,
      newH = container.scrollHeight
    canvas.width = newW
    canvas.height = newH
    if (prevW > 0 && prevH > 0) {
      const sx = newW / prevW,
        sy = newH / prevH
      for (const p of particles) {
        p.x *= sx
        p.y *= sy
      }
    }
    prevW = newW
    prevH = newH
  }
  resize()
  const ro = new ResizeObserver(resize)
  ro.observe(container)
  for (let i = 0; i < COUNT; i++) {
    const a = Math.random() * Math.PI * 2
    const s = 0.1 + Math.random() * 0.25
    particles.push({
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height,
      r: 1 + Math.random() * 2,
      dx: Math.cos(a) * s,
      dy: Math.sin(a) * s,
      o: 0.15 + Math.random() * 0.3,
    })
  }
  function draw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height)
    for (const p of particles) {
      p.x += p.dx
      p.y += p.dy
      if (p.x < -10) p.x = canvas.width + 10
      if (p.x > canvas.width + 10) p.x = -10
      if (p.y < -10) p.y = canvas.height + 10
      if (p.y > canvas.height + 10) p.y = -10
      ctx.beginPath()
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2)
      ctx.fillStyle = `rgba(139,132,255,${p.o})`
      ctx.fill()
    }
    particleRaf = requestAnimationFrame(draw)
  }
  draw()
  return () => {
    ro.disconnect()
    if (particleRaf) cancelAnimationFrame(particleRaf)
  }
}
let cleanupParticles = null

// ---- Lifecycle / polling ----
const npVisible = ref(false)
const npSession = ref({})
const timers = []
let secondaryLoadStarted = false

function openFullscreen(session) {
  npSession.value = session
  npVisible.value = true
}

function queueDeferredLoad(task) {
  if (typeof window !== 'undefined' && typeof window.requestIdleCallback === 'function') {
    window.requestIdleCallback(
      () => {
        void task()
      },
      { timeout: 1500 },
    )
    return
  }
  window.setTimeout(() => {
    void task()
  }, 0)
}

function startPrimaryPolling() {
  timers.push(
    setInterval(loadSystemStats, 10000),
    setInterval(loadSessions, 15000),
    setInterval(loadServices, 60000),
  )
}

function startSecondaryPolling() {
  timers.push(
    setInterval(loadLogs, 15000),
    setInterval(loadAlerts, 30000),
    setInterval(loadMediaStats, 60000),
    setInterval(loadWatchlist, 30000),
  )
}

function scheduleSecondaryLoad() {
  if (secondaryLoadStarted) return
  secondaryLoadStarted = true
  queueDeferredLoad(async () => {
    await Promise.all([
      loadLogs(),
      loadAlerts(),
      loadDuplicates(),
      loadWatchlist(),
      loadMediaStats(),
      loadLeaderboard(),
    ])
    startSecondaryPolling()
  })
}

onMounted(async () => {
  await nextTick()
  if (particlesEnabled.value) cleanupParticles = initParticles()
  await loadLayout()
  await Promise.all([loadSeenAlerts(), loadSystemStats(), loadServices(), loadSessions()])
  startPrimaryPolling()
  scheduleSecondaryLoad()
})
onActivated(() => {
  if (!cleanupParticles && particlesEnabled.value) cleanupParticles = initParticles()
})
onDeactivated(() => {
  if (cleanupParticles) {
    cleanupParticles()
    cleanupParticles = null
  }
})
onUnmounted(() => {
  timers.forEach(clearInterval)
  if (cleanupParticles) cleanupParticles()
})
</script>
