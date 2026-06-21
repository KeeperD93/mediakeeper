<template>
  <HealthScore v-if="id === WIDGET_ID.HEALTH_SCORE" />
  <RequestsActionCard v-else-if="id === WIDGET_ID.PORTAL_ACTION" />
  <PortalEngagementCard v-else-if="id === WIDGET_ID.PORTAL_ENGAGEMENT" />
  <PortalUpcomingEventsCard v-else-if="id === WIDGET_ID.PORTAL_EVENTS" />
  <ActivityTimeline
    v-else-if="id === WIDGET_ID.ACTIVITY"
    :logs="logs"
    :alerts="alerts"
    :sessions="sessions"
    :seen-alert-ids="seenAlertIds"
    :emby-base-url="embyBaseUrl"
  />
  <UpcomingEpisodes v-else-if="id === WIDGET_ID.UPCOMING" />
  <LeaderboardCard
    v-else-if="id === WIDGET_ID.TOP_USERS"
    :entries="leaderboardEntries.slice(0, 3)"
    widget
  />
  <Heatmap v-else-if="id === WIDGET_ID.HEATMAP" />
  <QuickLink
    v-else-if="id === WIDGET_ID.LINK_WATCHLIST"
    :title="watchlistLabel"
    :subtitle="
      watchlistScanAgo ? $t('dashboard.lastScan') + ' ' + watchlistScanAgo : $t('sidebar.watchlist')
    "
    route="/watchlist"
    icon-bg="rgb(var(--color-module-watchlist-rgb), 0.12)"
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
import { WIDGET_ID } from '@/composables/useDashboardLayout'

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
  color: var(--color-module-watchlist);
}
</style>
