<template>
  <div class="m-dash-stats">
    <StatCard
      v-if="!hidden.includes(WIDGET_ID.STAT_PLAYS)"
      :label="$t('dashboard.totalPlays')"
      :value="mediaStats.plays"
      route="/stats"
      :icon="Play"
      :accent="STAT_CARD_ACCENT.plays"
    />
    <StatCard
      v-if="!hidden.includes(WIDGET_ID.STAT_DURATION)"
      :label="$t('dashboard.totalDuration')"
      :value="mediaStats.duration"
      :icon="Clock"
      :accent="STAT_CARD_ACCENT.duration"
    />
    <StatCard
      v-if="!hidden.includes(WIDGET_ID.STAT_DUPLICATES)"
      :label="$t('dashboard.duplicates')"
      :value="duplicatesCount"
      route="/duplicates"
      :icon="Copy"
      :accent="STAT_CARD_ACCENT.duplicates"
      :color="duplicatesCount !== '0' && duplicatesCount !== '—' ? STAT_CARD_ACCENT.duplicates : ''"
    />
    <StatCard
      v-if="!hidden.includes(WIDGET_ID.STAT_STORAGE)"
      :label="$t('dashboard.storage')"
      :value="mediaStats.storage"
      :icon="HardDrive"
      :accent="STAT_CARD_ACCENT.storage"
    />
  </div>
</template>

<script setup>
import { Play, Clock, Copy, HardDrive } from 'lucide-vue-next'
import StatCard from '@/components/dashboard/widgets/StatCard.vue'
import { WIDGET_ID } from '@/composables/useDashboardLayout'
import { STAT_CARD_ACCENT } from '@/constants/dashboardStatColors'

defineProps({
  hidden: { type: Array, default: () => [] },
  duplicatesCount: { type: [String, Number], default: '—' },
  mediaStats: {
    type: Object,
    default: () => ({ plays: '—', duration: '—', storage: '—' }),
  },
})
</script>

<style scoped>
.m-dash-stats {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

/* Compact StatCard on mobile — the default sizing was tuned for the
   desktop 36-column grid where each card is much wider. We shrink the
   icon, the value font, and the label to keep the stats strip light
   above the reorderable stack. */
.m-dash-stats :deep(.wg-stat) {
  padding: 8px 10px;
}
.m-dash-stats :deep(.wg-stat-body) {
  gap: 8px;
}
.m-dash-stats :deep(.wg-stat-icon) {
  width: 34px;
  height: 34px;
  border-radius: var(--radius-input);
}
.m-dash-stats :deep(.wg-stat-icon svg) {
  width: 16px;
  height: 16px;
}
.m-dash-stats :deep(.wg-stat-label) {
  font-size: var(--text-3xs);
  letter-spacing: 0.2px;
}
.m-dash-stats :deep(.wg-stat-val) {
  font-size: var(--text-lg);
  margin-top: 2px;
}
</style>
