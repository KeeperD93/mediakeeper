<template>
  <div class="wls-kpis">
    <div class="wls-kpi glass-kpi">
      <span class="wls-kpi-val wls-kpi-val-missing">{{ missingCount }}</span>
      <span class="wls-kpi-label">{{ $t('watchlist.missingEpisodes') }}</span>
      <span class="wls-kpi-sub">
        {{ $t('watchlist.outOfSeries', { count: filteredSeriesCount }) }}
      </span>
    </div>
    <div class="wls-kpi glass-kpi">
      <span class="wls-kpi-val wls-kpi-val-upcoming">{{ upcomingCount }}</span>
      <span class="wls-kpi-label">{{ $t('watchlist.upcoming') }}</span>
      <span class="wls-kpi-sub">{{ $t('watchlist.upcomingEpisodes') }}</span>
    </div>
    <div class="wls-kpi glass-kpi">
      <span class="wls-kpi-val wls-kpi-val-tracked">{{ trackedCount }}</span>
      <span class="wls-kpi-label">{{ $t('watchlist.trackedContent') }}</span>
      <span class="wls-kpi-sub">{{ $t('watchlist.active') }}</span>
    </div>
    <div class="wls-kpi glass-kpi">
      <span class="wls-kpi-val wls-kpi-val-ignored">{{ ignoredCount }}</span>
      <span class="wls-kpi-label">{{ $t('watchlist.ignoredEpisodes') }}</span>
      <span class="wls-kpi-sub">{{ $t('watchlist.hidden') }}</span>
    </div>
  </div>
</template>

<script setup>
defineProps({
  missingCount: { type: Number, required: true },
  upcomingCount: { type: Number, required: true },
  trackedCount: { type: Number, required: true },
  ignoredCount: { type: Number, required: true },
  filteredSeriesCount: { type: Number, required: true },
})
</script>

<style scoped>
.wls-kpis {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
  margin-bottom: 20px;
}
.glass-kpi {
  background: var(--surface-1);
  backdrop-filter: var(--blur-sm);
  border: 0.5px solid var(--border-default);
  border-radius: var(--radius-card);
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 3px;
  transition: border-color var(--duration-base);
}
.glass-kpi:hover {
  border-color: rgb(99, 102, 241, 0.2);
}
.wls-kpi-val {
  font-size: 1.5rem;
  font-weight: var(--font-bold);
  font-family: 'SF Mono', 'Cascadia Mono', monospace;
  line-height: var(--lh-tight);
}
.wls-kpi-val-missing {
  color: var(--color-error);
}
.wls-kpi-val-upcoming {
  color: var(--color-info);
}
.wls-kpi-val-tracked {
  color: #a78bfa;
}
.wls-kpi-val-ignored {
  color: var(--color-warning);
}
.wls-kpi-label {
  font-size: var(--text-2xs);
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.wls-kpi-sub {
  font-size: var(--text-2xs);
  color: var(--text-secondary);
}

@media (max-width: 1024px) {
  .wls-kpis {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
