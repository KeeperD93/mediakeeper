<template>
  <div v-if="stats" class="lb-stats-bar" role="group">
    <span class="lb-stats-chip">
      <CalendarDays :size="14" :stroke-width="2.2" aria-hidden="true" />
      <span class="lb-stats-chip-text">{{ stats.period_label }}</span>
    </span>
    <span class="lb-stats-sep">·</span>
    <span class="lb-stats-chip">
      <Users :size="14" :stroke-width="2.2" aria-hidden="true" />
      <span class="lb-stats-chip-text">
        {{
          $t(
            'portal.leaderboard.stats.playersRanked',
            { n: displayedPlayers.toLocaleString() },
            totalPlayers,
          )
        }}
      </span>
    </span>
    <span class="lb-stats-sep">·</span>
    <span class="lb-stats-chip">
      <Zap :size="14" :stroke-width="2.2" aria-hidden="true" />
      <span class="lb-stats-chip-text">
        {{
          $t('portal.leaderboard.stats.activityXp', {
            n: displayedXp.toLocaleString(),
          })
        }}
      </span>
    </span>
    <span class="lb-stats-sep">·</span>
    <span class="lb-stats-chip">
      <Trophy :size="14" :stroke-width="2.2" aria-hidden="true" />
      <span class="lb-stats-chip-text">
        {{
          $t(
            'portal.leaderboard.stats.trophiesDistributed',
            { n: displayedTrophies.toLocaleString() },
            totalTrophies,
          )
        }}
      </span>
    </span>
    <template v-if="stats.days_remaining !== null">
      <span class="lb-stats-sep">·</span>
      <span class="lb-stats-chip">
        <svg
          class="lb-stats-progress"
          viewBox="0 0 24 24"
          :aria-label="
            $t(
              'portal.leaderboard.stats.daysRemaining',
              { n: stats.days_remaining },
              stats.days_remaining,
            )
          "
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
          {{
            $t(
              'portal.leaderboard.stats.daysRemaining',
              { n: stats.days_remaining },
              stats.days_remaining,
            )
          }}
        </span>
      </span>
    </template>
  </div>
</template>

<script setup>
import { computed, toRef } from 'vue'
import { CalendarDays, Trophy, Users, Zap } from 'lucide-vue-next'

import { useCountUp } from '@/composables/portal/useCountUp'

const props = defineProps({
  stats: { type: Object, default: null },
})

const statsRef = toRef(props, 'stats')
const totalPlayers = computed(() => statsRef.value?.total_players || 0)
const totalXp = computed(() => statsRef.value?.total_xp || 0)
const totalTrophies = computed(() => statsRef.value?.total_trophies || 0)

const { displayed: displayedPlayers } = useCountUp(totalPlayers, { duration: 1100 })
const { displayed: displayedXp } = useCountUp(totalXp, { duration: 1500 })
const { displayed: displayedTrophies } = useCountUp(totalTrophies, { duration: 1100 })

const circ = 2 * Math.PI * 10
// The calendar of the days left beside it, the server's: the browser may be elsewhere.
const monthElapsedPct = computed(() => {
  const totalDays = statsRef.value?.days_in_month
  if (!totalDays) return 0
  return Math.min(1, Math.max(0, (totalDays - statsRef.value.days_remaining) / totalDays))
})
</script>

<style scoped>
.lb-stats-bar {
  position: sticky;
  top: 0;
  z-index: 10;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  padding: 12px 18px;
  margin: 16px 0 20px;
  border-radius: var(--portal-radius-lg);
  background: rgb(var(--accent-rgb), 0.04);
  backdrop-filter: blur(12px);
  border: 1px solid var(--portal-border-default);
}
.lb-stats-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: var(--portal-text-xs);
  color: var(--portal-text-body);
  font-weight: var(--portal-font-medium);
  white-space: nowrap;
}
.lb-stats-chip-text {
  font-variant-numeric: tabular-nums;
}
.lb-stats-chip svg:not(.lb-stats-progress) {
  color: var(--portal-accent-400);
}
/* Chips wrap below 1024px, where a separator could end up alone at a line end. */
.lb-stats-sep {
  display: none;
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
  stroke: var(--portal-border-intense);
  stroke-width: 3;
}
.lb-stats-progress-fill {
  fill: none;
  stroke: var(--portal-accent-400);
  stroke-width: 3;
  stroke-linecap: round;
  transition: stroke-dashoffset var(--portal-dur-slow) var(--portal-ease-emphasis);
}
@media (min-width: 1024px) {
  .lb-stats-sep {
    display: inline;
  }
}
@media (max-width: 640px) {
  /* Several lines here: stuck to the top, they would hide the ranking. */
  .lb-stats-bar {
    position: static;
    padding: 8px 12px;
    margin: 12px 0 16px;
    gap: 6px 12px;
  }
  .lb-stats-chip {
    font-size: var(--portal-text-2xs);
  }
}
</style>
