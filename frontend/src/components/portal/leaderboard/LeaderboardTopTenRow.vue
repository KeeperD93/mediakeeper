<template>
  <router-link
    v-if="entry"
    :to="entry.user_id ? { name: 'portal-user-profile', params: { id: entry.user_id } } : ''"
    class="lb-top-row"
    :class="{
      'lb-top-row--me': entry.is_current_user,
      'lb-top-row--trophies': entry.trophies_won > 0,
    }"
  >
    <span class="gc-lb-pos lb-top-row-rank">{{ entry.rank }}</span>
    <div class="gc-lb-av lb-top-row-av">
      <MkAvatar
        :name="entry.display_name || ''"
        :src="entry.avatar_url || null"
        :size="40"
        :tier="entry.tier || 'bronze'"
      />
    </div>
    <div class="lb-top-row-info">
      <span class="lb-top-row-pseudo">
        <span class="lb-top-row-name">{{ entry.display_name }}</span>
        <LeaderboardMePill v-if="entry.is_current_user" />
      </span>
      <span class="lb-top-row-title">
        <LeaderboardLevelTitle :entry="entry" />
      </span>
    </div>
    <span class="lb-top-row-figures">
      <LeaderboardTrophies :count="entry.trophies_won" />
      <LeaderboardMove
        class="lb-top-row-move"
        :movement="entry.movement"
        :period="period"
        :size="10"
      />
    </span>
    <span class="lb-top-row-xp">{{ (entry.period_xp || 0).toLocaleString() }} XP</span>
  </router-link>
</template>

<script setup>
import MkAvatar from '@/components/common/MkAvatar.vue'
import LeaderboardLevelTitle from '@/components/portal/leaderboard/LeaderboardLevelTitle.vue'
import LeaderboardMePill from '@/components/portal/leaderboard/LeaderboardMePill.vue'
import LeaderboardMove from '@/components/portal/leaderboard/LeaderboardMove.vue'
import LeaderboardTrophies from '@/components/portal/leaderboard/LeaderboardTrophies.vue'
import { LEADERBOARD_PERIOD } from '@/constants/leaderboard'

defineProps({
  entry: { type: Object, default: null },
  index: { type: Number, default: 0 },
  period: { type: String, default: LEADERBOARD_PERIOD.MONTH },
})
</script>

<style scoped>
.lb-top-row {
  display: grid;
  grid-template-columns: 36px 40px minmax(0, 1fr) auto var(--portal-leaderboard-xp-width);
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  min-height: 64px;
  border-radius: var(--portal-radius-md);
  background: var(--portal-surface-1);
  border: 1px solid var(--portal-border-subtle);
  color: var(--portal-text-primary);
  text-decoration: none;
  transition:
    transform var(--portal-dur-base) var(--portal-ease-emphasis),
    box-shadow var(--portal-dur-base) var(--portal-ease-emphasis),
    border-color var(--portal-dur-base) var(--portal-ease-emphasis);
}
.lb-top-row--me {
  background: var(--portal-row-me-bg);
  border-left: var(--portal-border-width-accent) solid var(--portal-accent-500);
}
@media (hover: hover) {
  .lb-top-row:hover {
    transform: translateY(-2px);
    box-shadow: var(--portal-shadow-sm);
  }
}
.lb-top-row-av {
  width: 40px;
  height: 40px;
}
.lb-top-row-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
}
/* The label goes under a name that needs the room, and only the name can be
   cut: the label and the XP stay whole. */
.lb-top-row-pseudo {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 2px 6px;
  min-width: 0;
  font-size: var(--portal-text-base);
  font-weight: var(--portal-font-medium);
  color: var(--portal-text-primary);
}
.lb-top-row-name {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.lb-top-row-title {
  font-size: var(--portal-text-3xs);
  text-transform: uppercase;
  letter-spacing: var(--portal-tracking-caps);
  color: var(--portal-text-muted);
}
.lb-top-row-figures {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
.lb-top-row-move {
  min-width: 36px;
}
.lb-top-row-xp {
  font-family: var(--portal-font-display);
  font-size: var(--portal-text-base);
  font-weight: var(--portal-font-bold);
  color: var(--portal-color-info-light);
  text-align: right;
  font-variant-numeric: tabular-nums;
}
@media (max-width: 640px) {
  .lb-top-row {
    grid-template-columns: 36px 36px minmax(0, 1fr) auto;
    gap: 0 8px;
    padding: 8px 12px;
    min-height: 56px;
  }
  .lb-top-row-move {
    display: none;
  }
  .lb-top-row-rank,
  .lb-top-row-av {
    grid-row: 1 / span 2;
  }
  .lb-top-row-av {
    width: 36px;
    height: 36px;
  }
  /* The titles take their own line, the full width of the row: next to the XP,
     a long one would not fit on a small phone. */
  .lb-top-row-info {
    display: contents;
  }
  .lb-top-row-pseudo {
    grid-row: 1;
    grid-column: 3;
  }
  .lb-top-row-xp {
    grid-row: 1;
    grid-column: 4;
  }
  .lb-top-row-title {
    grid-row: 2;
    grid-column: 3 / -1;
  }
  /* The trophies go under the XP: next to the name, they would squeeze it. */
  .lb-top-row-figures {
    grid-row: 2;
    grid-column: 4;
    place-self: start end;
  }
  .lb-top-row--trophies .lb-top-row-title {
    grid-column: 3;
  }
  /* The XP against the top and the trophies against the bottom, without the space a
     line of text keeps above its digits: the same room on both sides of the row. */
  .lb-top-row--trophies .lb-top-row-xp {
    align-self: start;
    line-height: var(--portal-lh-tight);
    text-box: trim-both cap alphabetic;
  }
  .lb-top-row--trophies .lb-top-row-figures {
    place-self: end;
  }
}
</style>
