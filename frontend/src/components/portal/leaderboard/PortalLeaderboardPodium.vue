<template>
  <div v-if="entries.length" class="pt-lb-podium" :data-count="entries.length">
    <router-link
      v-for="(entry, idx) in entries"
      :key="entry.user_id"
      :to="{ name: 'portal-user-profile', params: { id: entry.user_id } }"
      class="pt-lb-podium-card"
      :class="`pt-lb-podium-card--${rankFor(idx)}`"
    >
      <div class="pt-lb-podium-rank">#{{ rankFor(idx) }}</div>
      <component
        :is="medalFor(idx)"
        :size="22"
        :stroke-width="2.5"
        class="pt-lb-podium-medal"
        aria-hidden="true"
      />
      <div class="gc-lb-av">
        <MkAvatar
          :name="entry.display_name || ''"
          :src="entry.avatar_url || null"
          :size="84"
          :tier="entry.tier || 'bronze'"
        />
      </div>
      <div class="pt-lb-podium-name">{{ entry.display_name }}</div>
      <LeaderboardMePill v-if="entry.is_current_user" />
      <div class="pt-lb-podium-meta">
        <span class="pt-lb-podium-level">{{ $t('portal.level') }} {{ entry.level }}</span>
        <span class="pt-lb-podium-title">
          {{ $t(`portal.profile.titles.${entry.title_key || 'spectator'}`) }}
          <LeaderboardChosenTitle :entry="entry" />
        </span>
      </div>
      <div class="pt-lb-podium-xp">{{ (entry.period_xp || 0).toLocaleString() }} XP</div>
      <div class="pt-lb-podium-figures">
        <LeaderboardTrophies :count="entry.trophies_won" />
        <LeaderboardMove
          class="pt-lb-podium-move"
          :movement="entry.movement"
          :period="period"
          :size="11"
        />
      </div>
    </router-link>
  </div>
</template>

<script setup>
import { Award, Medal } from 'lucide-vue-next'
import MkAvatar from '@/components/common/MkAvatar.vue'
import LeaderboardChosenTitle from '@/components/portal/leaderboard/LeaderboardChosenTitle.vue'
import LeaderboardMePill from '@/components/portal/leaderboard/LeaderboardMePill.vue'
import LeaderboardMove from '@/components/portal/leaderboard/LeaderboardMove.vue'
import LeaderboardTrophies from '@/components/portal/leaderboard/LeaderboardTrophies.vue'
import { LEADERBOARD_PERIOD } from '@/constants/leaderboard'

defineProps({
  entries: { type: Array, default: () => [] },
  period: { type: String, default: LEADERBOARD_PERIOD.MONTH },
})

// Parent slices ``items.slice(1, 3)``: idx 0 → rank 2, idx 1 → rank 3.
function rankFor(idx) {
  return idx + 2
}
function medalFor(idx) {
  return idx === 0 ? Award : Medal
}
</script>

<style scoped>
.pt-lb-podium {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}
.pt-lb-podium[data-count='1'] {
  grid-template-columns: minmax(0, 480px);
  justify-content: center;
}
.pt-lb-podium-card {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 24px 16px 18px;
  min-height: 280px;
  border-radius: var(--portal-radius-lg);
  text-decoration: none;
  color: var(--portal-text-primary);
  background: var(--portal-surface-1);
  transition:
    transform var(--portal-dur-med) var(--portal-ease-emphasis),
    box-shadow var(--portal-dur-med) var(--portal-ease-emphasis),
    border-color var(--portal-dur-med) var(--portal-ease-emphasis);
}
.pt-lb-podium-card--2 {
  border: 1px solid rgb(192, 192, 192, 0.3);
}
.pt-lb-podium-card--3 {
  border: 1px solid rgb(205, 127, 50, 0.3);
}
@media (hover: hover) {
  .pt-lb-podium-card:hover {
    transform: translateY(-4px);
    box-shadow: var(--portal-shadow-popup);
  }
}
.pt-lb-podium-medal {
  position: absolute;
  top: 14px;
  right: 14px;
}
.pt-lb-podium-card--2 .pt-lb-podium-medal {
  color: #c0c0c0;
}
.pt-lb-podium-card--3 .pt-lb-podium-medal {
  color: #cd7f32;
}
.pt-lb-podium-rank {
  font-size: var(--portal-text-2xl);
  font-weight: var(--portal-font-black);
  font-family: var(--portal-font-display);
  line-height: 1;
}
.pt-lb-podium-card--2 .pt-lb-podium-rank {
  color: #c0c0c0;
}
.pt-lb-podium-card--3 .pt-lb-podium-rank {
  color: #cd7f32;
}
.pt-lb-podium-card :deep(.gc-lb-av) {
  width: 84px;
  height: 84px;
}
/* Thicker ring on the larger podium avatar so the tier colour reads at this
   scale. Set on the avatar element itself so it wins over the 2px the
   ``.mk-avatar-tier--{tier}`` class sets there; legendary is excluded since it
   draws its ring via the ::after rainbow band, not the solid border. */
.pt-lb-podium-card :deep(.mk-avatar:not(.mk-avatar-tier--legendary)) {
  --mk-avatar-ring-width: 3px;
}
/* Legendary draws its ring via the ::after rainbow band (no solid border), so
   widen its band to the same 3px the other tiers get above — otherwise a
   level-50 podium avatar reads visibly thinner than a master next to it. */
.pt-lb-podium-card :deep(.mk-avatar-tier--legendary)::after {
  padding: 3px;
}
.pt-lb-podium-name {
  font-size: var(--portal-text-lg);
  font-weight: var(--portal-font-bold);
  text-align: center;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.pt-lb-podium-meta {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  font-size: var(--portal-text-3xs);
  color: var(--portal-text-muted);
  text-align: center;
  text-transform: uppercase;
  letter-spacing: var(--portal-tracking-caps);
}
.pt-lb-podium-xp {
  font-size: var(--portal-text-xl);
  font-weight: var(--portal-font-extrabold);
  font-family: var(--portal-font-display);
}
.pt-lb-podium-card--2 .pt-lb-podium-xp {
  color: #c0c0c0;
}
.pt-lb-podium-card--3 .pt-lb-podium-xp {
  color: #cd7f32;
}
.pt-lb-podium-figures {
  display: flex;
  align-items: center;
  gap: 8px;
}
.pt-lb-podium-move {
  min-width: 36px;
}
@media (max-width: 640px) {
  /* Two small cards side by side: the ranking must start within the first screen. */
  .pt-lb-podium {
    gap: 8px;
    margin-bottom: 16px;
  }
  .pt-lb-podium-card {
    gap: 4px;
    min-height: 0;
    padding: 12px 8px 10px;
  }
  .pt-lb-podium-rank {
    position: absolute;
    top: 10px;
    left: 12px;
    font-size: var(--portal-text-lg);
  }
  .pt-lb-podium-medal {
    top: 10px;
    right: 10px;
    width: 16px;
    height: 16px;
  }
  .pt-lb-podium-card :deep(.gc-lb-av) {
    width: 48px;
    height: 48px;
  }
  .pt-lb-podium-card :deep(.mk-avatar) {
    flex-shrink: 0;
    transform: scale(calc(48 / 84));
  }
  .pt-lb-podium-name {
    font-size: var(--portal-text-sm);
  }
  .pt-lb-podium-xp {
    font-size: var(--portal-text-md);
  }
}
</style>
