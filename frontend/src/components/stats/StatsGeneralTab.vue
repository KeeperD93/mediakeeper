<template>
  <div class="tab-panel">
    <StatsTotalsRow />
    <StatsSessionsSection />
    <StatsPlaybackCards ref="playbackRef" />
    <StatsLibrariesSection />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useStats } from '@/composables/useStats'
import StatsTotalsRow from '@/components/stats/StatsTotalsRow.vue'
import StatsSessionsSection from '@/components/stats/StatsSessionsSection.vue'
import StatsPlaybackCards from '@/components/stats/StatsPlaybackCards.vue'
import StatsLibrariesSection from '@/components/stats/StatsLibrariesSection.vue'

const { loadTotals, loadSparklines, loadRecords, loadLibraries, loadMinimap24h } = useStats()
const playbackRef = ref(null)

onMounted(async () => {
  await Promise.all([
    loadTotals(), loadSparklines(), loadRecords(),
    loadLibraries(), loadMinimap24h(),
  ])
  playbackRef.value?.loadPlaybackAndResolve(365)
})
</script>
