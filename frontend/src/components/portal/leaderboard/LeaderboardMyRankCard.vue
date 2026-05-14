<template>
  <component
    :is="effectiveOnPodium ? 'button' : 'div'"
    v-if="effectiveEntry"
    class="lb-my-rank"
    :class="{ 'lb-my-rank--podium': effectiveOnPodium }"
    :type="effectiveOnPodium ? 'button' : null"
    @click="effectiveOnPodium ? scrollToHero() : null"
  >
    <span class="lb-my-rank-label">{{ $t('portal.leaderboard.myRank.label') }}</span>
    <div class="lb-my-rank-avatar" :class="`gc-lb-av gc-lb-av--${effectiveEntry.tier || 'bronze'}`">
      <MkAvatar
        :name="effectiveEntry.display_name || ''"
        :src="effectiveEntry.avatar_url || null"
        :size="36"
      />
    </div>
    <div class="lb-my-rank-pseudo">{{ effectiveEntry.display_name }}</div>
    <div class="lb-my-rank-rank">#{{ effectiveRank }}</div>
    <div v-if="effectiveOnPodium" class="lb-my-rank-podium-msg">
      {{ $t('portal.leaderboard.myRank.onPodium') }}
    </div>
    <div v-else class="lb-my-rank-stats">
      <div class="lb-my-rank-stat">
        <span class="lb-my-rank-stat-label">{{ $t('portal.leaderboard.myRank.xpThisMonth') }}</span>
        <span class="lb-my-rank-stat-value">{{ (stats?.my_xp_month || 0).toLocaleString() }}</span>
      </div>
      <div class="lb-my-rank-stat">
        <span class="lb-my-rank-stat-label">
          {{
            $t('portal.leaderboard.myRank.deltaWeek', {
              n: (stats?.my_delta_week || 0).toLocaleString(),
            })
          }}
        </span>
      </div>
      <div v-if="stats?.projected_end_rank" class="lb-my-rank-stat">
        <span class="lb-my-rank-stat-label">{{ $t('portal.leaderboard.myRank.projectedEnd') }}</span>
        <span class="lb-my-rank-stat-value">#{{ stats.projected_end_rank }}</span>
      </div>
    </div>
  </component>
</template>

<script setup>
import { computed } from 'vue'

import MkAvatar from '@/components/common/MkAvatar.vue'

const props = defineProps({
  viewerRank: { type: Number, default: null },
  viewerEntry: { type: Object, default: null },
  inListEntry: { type: Object, default: null },
  stats: { type: Object, default: null },
})

const effectiveEntry = computed(() => props.inListEntry || props.viewerEntry || null)
const effectiveRank = computed(() => {
  if (props.inListEntry?.rank) return props.inListEntry.rank
  return props.viewerRank || null
})
const effectiveOnPodium = computed(() => {
  const r = effectiveRank.value
  return r != null && r <= 3
})

function scrollToHero() {
  if (typeof document === 'undefined') return
  const targetId = effectiveRank.value === 1 ? 'lb-hero' : 'lb-podium'
  const target = document.getElementById(targetId)
  if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' })
}
</script>

<style scoped>
.lb-my-rank {
  display: grid;
  grid-template-columns: auto auto 1fr auto auto;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 14px 18px;
  margin: 16px 0 24px;
  border-radius: var(--portal-radius-lg);
  background:
    linear-gradient(135deg, rgb(var(--accent-rgb), 0.1), transparent 70%),
    var(--portal-surface-1);
  border-left: 4px solid var(--accent-500);
  border-top: 1px solid rgb(255, 255, 255, 0.06);
  border-right: 1px solid rgb(255, 255, 255, 0.06);
  border-bottom: 1px solid rgb(255, 255, 255, 0.06);
  color: var(--portal-text-primary);
  text-align: left;
  cursor: default;
}
.lb-my-rank--podium {
  cursor: pointer;
  background:
    linear-gradient(135deg, rgb(var(--portal-color-warning-rgb), 0.12), transparent 70%),
    var(--portal-surface-1);
  border-left-color: var(--portal-color-warning);
}
.lb-my-rank-label {
  font-size: var(--portal-text-2xs);
  font-weight: var(--portal-font-bold);
  letter-spacing: var(--portal-tracking-widest);
  text-transform: uppercase;
  color: var(--portal-text-body-muted);
  opacity: 0.85;
}
.lb-my-rank-avatar {
  width: 44px;
  height: 44px;
}
.lb-my-rank-pseudo {
  font-size: var(--portal-text-base);
  font-weight: var(--portal-font-bold);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  min-width: 0;
}
.lb-my-rank-rank {
  font-family: var(--portal-font-display);
  font-size: clamp(2rem, 4vw, 3rem);
  font-weight: var(--portal-font-black);
  line-height: 1;
  color: var(--accent);
  font-variant-numeric: tabular-nums;
}
.lb-my-rank--podium .lb-my-rank-rank {
  color: var(--portal-color-warning);
}
.lb-my-rank-stats {
  display: flex;
  align-items: center;
  gap: 16px;
  font-size: var(--portal-text-xs);
  color: var(--portal-text-body-muted);
}
.lb-my-rank-stat {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.lb-my-rank-stat-label {
  font-size: var(--portal-text-3xs);
  text-transform: uppercase;
  letter-spacing: var(--portal-tracking-caps);
  color: var(--portal-text-muted);
}
.lb-my-rank-stat-value {
  font-family: var(--portal-font-display);
  font-size: var(--portal-text-md);
  font-weight: var(--portal-font-bold);
  color: var(--portal-text-primary);
  font-variant-numeric: tabular-nums;
}
.lb-my-rank-podium-msg {
  font-size: var(--portal-text-sm);
  font-weight: var(--portal-font-bold);
  color: var(--portal-color-warning);
}
@media (max-width: 640px) {
  .lb-my-rank {
    grid-template-columns: auto auto 1fr;
    grid-template-rows: auto auto;
    gap: 8px 10px;
    padding: 12px 14px;
  }
  .lb-my-rank-rank {
    grid-row: 1;
    grid-column: 4 / -1;
    justify-self: end;
  }
  .lb-my-rank-stats,
  .lb-my-rank-podium-msg {
    grid-column: 1 / -1;
    flex-wrap: wrap;
  }
}
</style>
