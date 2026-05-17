<template>
  <div class="m-dash-stats">
    <StatCard
      v-if="!hidden.includes(WIDGET_ID.STAT_PLAYS)"
      :label="$t('dashboard.totalPlays')"
      :value="mediaStats.plays"
      route="/stats"
      :icon="Play"
      accent="#6366f1"
    />
    <StatCard
      v-if="!hidden.includes(WIDGET_ID.STAT_DURATION)"
      :label="$t('dashboard.totalDuration')"
      :value="mediaStats.duration"
      :icon="Clock"
      accent="#10b981"
    />
    <StatCard
      v-if="!hidden.includes(WIDGET_ID.STAT_DUPLICATES)"
      :label="$t('dashboard.duplicates')"
      :value="duplicatesCount"
      route="/duplicates"
      :icon="Copy"
      accent="#f43f5e"
      :color="duplicatesCount !== '0' && duplicatesCount !== '—' ? '#f43f5e' : ''"
    />
    <StatCard
      v-if="!hidden.includes(WIDGET_ID.STAT_STORAGE)"
      :label="$t('dashboard.storage')"
      :value="mediaStats.storage"
      :icon="HardDrive"
      accent="#f59e0b"
    />
  </div>
</template>

<script setup>
import { Play, Clock, Copy, HardDrive } from 'lucide-vue-next'
import StatCard from '@/components/dashboard/widgets/StatCard.vue'
import { WIDGET_ID } from '@/composables/useDashboardLayout'

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
  gap: 10px;
}
</style>
