<template>
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
  <LeaderboardCard v-else-if="id === 'topUsers'" :entries="leaderboardEntries.slice(0, 3)" widget />
  <Heatmap v-else-if="id === 'heatmap'" />
  <QuickLink
    v-else-if="id === 'linkWatchlist'"
    :title="watchlistLabel"
    :subtitle="
      watchlistScanAgo ? $t('dashboard.lastScan') + ' ' + watchlistScanAgo : $t('sidebar.watchlist')
    "
    route="/watchlist"
    icon-bg="rgba(139,92,246,0.12)"
  >
    <template #icon><ClipboardCheck class="m-dash-ql-icon" :size="18" /></template>
  </QuickLink>
</template>

<script setup>
import { ClipboardCheck } from 'lucide-vue-next'
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
  id: { type: String, required: true },
  logs: { type: Array, default: () => [] },
  alerts: { type: Array, default: () => [] },
  sessions: { type: Array, default: () => [] },
  seenAlertIds: { type: Set, default: () => new Set() },
  embyBaseUrl: { type: String, default: '' },
  watchlistLabel: { type: String, default: '' },
  watchlistScanAgo: { type: String, default: '' },
  leaderboardEntries: { type: Array, default: () => [] },
})
</script>

<style scoped>
.m-dash-ql-icon {
  /* Pre-existing brand-violet for the watchlist QuickLink icon —
     no token captures this hue yet (debt flagged separately). */
  color: #8b5cf6;
}
</style>
