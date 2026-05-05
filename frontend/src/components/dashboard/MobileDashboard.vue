<template>
  <div class="m-dash">
    <!-- Row of quick stats — compact 2x2 grid on phones. -->
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

    <HealthScore v-if="!hidden.includes('healthScore')" class="m-dash-card" />

    <RequestsActionCard v-if="!hidden.includes('portalAction')" class="m-dash-card" />
    <PortalEngagementCard v-if="!hidden.includes('portalEngagement')" class="m-dash-card" />
    <PortalUpcomingEventsCard v-if="!hidden.includes('portalEvents')" class="m-dash-card" />

    <ActivityTimeline
      v-if="!hidden.includes('activity')"
      class="m-dash-card"
      :logs="logs"
      :alerts="alerts"
      :sessions="sessions"
      :seen-alert-ids="seenAlertIds"
      :emby-base-url="embyBaseUrl"
    />

    <UpcomingEpisodes v-if="!hidden.includes('upcoming')" class="m-dash-card" />

    <LeaderboardCard
      v-if="!hidden.includes('topUsers')"
      class="m-dash-card"
      :entries="leaderboardEntries.slice(0, 3)"
      widget
    />

    <Heatmap v-if="!hidden.includes('heatmap')" class="m-dash-card" />

    <QuickLink
      v-if="!hidden.includes('linkWatchlist')"
      class="m-dash-card"
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
</template>

<script setup>
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

defineProps({
  hidden: { type: Array, default: () => [] },
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
</script>

<style scoped>
.m-dash {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 12px 14px calc(60px + env(safe-area-inset-bottom, 0px));
}

.m-dash-stats {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.m-dash-card {
  min-height: 120px;
}

/* Dashboard widgets expect a grid parent with height: 100%. On mobile
   there's no grid cell — we give each widget a usable min-height so
   their content actually shows. */
.m-dash :deep(.wg-req),
.m-dash :deep(.wg-eng),
.m-dash :deep(.wg-evt),
.m-dash :deep(.wg-health),
.m-dash :deep(.uc),
.m-dash :deep(.hm) {
  min-height: 220px;
}
.m-dash :deep(.tl-root) {
  min-height: 340px;
}
.m-dash-ql-icon {
  color: #8b5cf6;
}
</style>
