<template>
  <LeaderboardCard v-model:period="period" :entries="entries" :loading="!isMonth && loading" />
</template>

<script setup>
import { computed, ref, watch } from 'vue'

import LeaderboardCard from '@/components/portal/profile/LeaderboardCard.vue'
import { useActivityLeaderboard } from '@/composables/portal/useActivityLeaderboard'
import { LEADERBOARD_PERIOD, LEADERBOARD_PROFILE_LIMIT } from '@/constants/leaderboard'

const props = defineProps({
  // The month comes with the profile, already loaded: it asks the server for nothing.
  monthEntries: { type: Array, default: () => [] },
})

const period = ref(LEADERBOARD_PERIOD.MONTH)
const { entries: top, viewerEntry, loading, fetchTop } = useActivityLeaderboard()

const isMonth = computed(() => period.value === LEADERBOARD_PERIOD.MONTH)

// A viewer outside the top comes last, as in the month the profile brings.
const entries = computed(() => {
  if (isMonth.value) return props.monthEntries
  return viewerEntry.value ? [...top.value, viewerEntry.value] : top.value
})

watch(period, () => {
  if (!isMonth.value) fetchTop(LEADERBOARD_PROFILE_LIMIT, { period: period.value })
})
</script>
