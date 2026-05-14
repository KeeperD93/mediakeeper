<template>
  <div v-if="stats" class="lb-stats-bar" role="group">
    <span class="lb-stats-chip">
      <CalendarDays :size="14" :stroke-width="2.2" aria-hidden="true" />
      <span class="lb-stats-chip-text">{{ stats.month_label }}</span>
    </span>
    <span class="lb-stats-sep">·</span>
    <span class="lb-stats-chip">
      <Users :size="14" :stroke-width="2.2" aria-hidden="true" />
      <span class="lb-stats-chip-text">
        {{
          $t('portal.leaderboard.stats.playersRanked', {
            n: displayedPlayers.toLocaleString(),
          })
        }}
      </span>
    </span>
    <span class="lb-stats-sep">·</span>
    <span class="lb-stats-chip">
      <Zap :size="14" :stroke-width="2.2" aria-hidden="true" />
      <span class="lb-stats-chip-text">
        {{
          $t('portal.leaderboard.stats.xpDistributed', {
            n: displayedXp.toLocaleString(),
          })
        }}
      </span>
    </span>
    <span class="lb-stats-sep">·</span>
    <span class="lb-stats-chip">
      <svg
        class="lb-stats-progress"
        viewBox="0 0 24 24"
        :aria-label="$t('portal.leaderboard.stats.daysRemaining', { n: stats.days_remaining })"
      >
        <circle class="lb-stats-progress-track" cx="12" cy="12" r="10" />
        <circle
          class="lb-stats-progress-fill"
          cx="12"
          cy="12"
          r="10"
          :stroke-dasharray="circ"
          :stroke-dashoffset="circ * (1 - monthElapsedPct)"
        />
      </svg>
      <span class="lb-stats-chip-text">
        {{ $t('portal.leaderboard.stats.daysRemaining', { n: stats.days_remaining }) }}
      </span>
    </span>
  </div>
</template>

<script setup>
import { computed, toRef } from 'vue'
import { CalendarDays, Users, Zap } from 'lucide-vue-next'

import { useCountUp } from '@/composables/portal/useCountUp'

const props = defineProps({
  stats: { type: Object, default: null },
})

const statsRef = toRef(props, 'stats')
const totalPlayers = computed(() => statsRef.value?.total_players || 0)
const totalXp = computed(() => statsRef.value?.total_xp_month || 0)

const { displayed: displayedPlayers } = useCountUp(totalPlayers.value, { duration: 1100 })
const { displayed: displayedXp } = useCountUp(totalXp.value, { duration: 1500 })

const circ = 2 * Math.PI * 10
const monthElapsedPct = computed(() => {
  const now = new Date()
  const totalDays = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate()
  return Math.min(1, Math.max(0, now.getDate() / totalDays))
})
</script>

<style scoped>
.lb-stats-bar {
  position: sticky;
  top: 0;
  z-index: 10;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 18px;
  margin: 16px 0 20px;
  border-radius: var(--portal-radius-lg);
  background: rgb(var(--accent-rgb), 0.04);
  backdrop-filter: blur(12px);
  border: 1px solid rgb(255, 255, 255, 0.08);
  overflow-x: auto;
  scrollbar-width: none;
  white-space: nowrap;
}
.lb-stats-bar::-webkit-scrollbar {
  display: none;
}
.lb-stats-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: var(--portal-text-xs);
  color: var(--portal-text-body);
  font-weight: var(--portal-font-medium);
}
.lb-stats-chip-text {
  font-variant-numeric: tabular-nums;
}
.lb-stats-chip svg:not(.lb-stats-progress) {
  color: var(--accent);
}
.lb-stats-sep {
  color: var(--portal-text-muted);
  opacity: 0.5;
  font-size: var(--portal-text-xs);
}
.lb-stats-progress {
  width: 16px;
  height: 16px;
  transform: rotate(-90deg);
}
.lb-stats-progress-track {
  fill: none;
  stroke: rgb(255, 255, 255, 0.1);
  stroke-width: 3;
}
.lb-stats-progress-fill {
  fill: none;
  stroke: var(--accent-500);
  stroke-width: 3;
  stroke-linecap: round;
  transition: stroke-dashoffset var(--portal-dur-slow) var(--portal-ease-emphasis);
}
@media (max-width: 640px) {
  .lb-stats-bar {
    padding: 10px 14px;
    gap: 10px;
  }
}
</style>
