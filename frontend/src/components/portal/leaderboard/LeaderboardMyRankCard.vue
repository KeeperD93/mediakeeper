<template>
  <div v-if="viewerEntry" class="lb-my-rank">
    <span class="lb-my-rank-label">{{ $t('portal.leaderboard.myRank.label') }}</span>
    <div class="lb-my-rank-avatar gc-lb-av">
      <MkAvatar
        :name="viewerEntry.display_name || ''"
        :src="viewerEntry.avatar_url || null"
        :size="44"
        :tier="viewerEntry.tier || 'bronze'"
      />
    </div>
    <div class="lb-my-rank-pseudo">{{ viewerEntry.display_name }}</div>
    <div class="lb-my-rank-rank">#{{ viewerRank }}</div>
    <div class="lb-my-rank-stats">
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
        <span class="lb-my-rank-stat-label">
          {{ $t('portal.leaderboard.myRank.projectedEnd') }}
        </span>
        <span class="lb-my-rank-stat-value">#{{ stats.projected_end_rank }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import MkAvatar from '@/components/common/MkAvatar.vue'

defineProps({
  viewerRank: { type: Number, default: null },
  viewerEntry: { type: Object, default: null },
  stats: { type: Object, default: null },
})
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
    linear-gradient(135deg, rgb(var(--accent-rgb), 0.1), transparent 70%), var(--portal-surface-1);
  border-left: 4px solid var(--accent-500);
  border-top: 1px solid rgb(255, 255, 255, 0.06);
  border-right: 1px solid rgb(255, 255, 255, 0.06);
  border-bottom: 1px solid rgb(255, 255, 255, 0.06);
  color: var(--portal-text-primary);
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
  color: var(--portal-color-info-light);
  font-variant-numeric: tabular-nums;
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
@media (max-width: 640px) {
  .lb-my-rank {
    grid-template-columns: auto auto 1fr;
    grid-template-rows: auto auto;
    gap: 6px 10px;
    padding: 10px 12px;
    margin: 12px 0 16px;
  }
  .lb-my-rank-rank {
    grid-row: 1;
    grid-column: 4 / -1;
    justify-self: end;
    font-size: var(--portal-text-xl);
  }
  .lb-my-rank-stats {
    grid-column: 1 / -1;
    flex-wrap: wrap;
    gap: 2px 12px;
  }
  .lb-my-rank-stat {
    flex-direction: row;
    align-items: baseline;
    gap: 4px;
  }
  .lb-my-rank-stat-value {
    font-size: var(--portal-text-sm);
  }
}
</style>
