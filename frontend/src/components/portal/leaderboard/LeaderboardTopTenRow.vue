<template>
  <router-link
    v-if="entry"
    :to="entry.user_id ? { name: 'portal-user-profile', params: { id: entry.user_id } } : ''"
    class="lb-top-row"
    :class="{ 'lb-top-row--me': entry.is_current_user }"
  >
    <span class="lb-top-row-rank" :class="`lb-top-row-rank--${entry.tier || 'bronze'}`">
      {{ entry.rank }}
    </span>
    <div class="gc-lb-av lb-top-row-av" :class="`gc-lb-av--${entry.tier || 'bronze'}`">
      <MkAvatar :name="entry.display_name || ''" :src="entry.avatar_url || null" :size="36" />
    </div>
    <div class="lb-top-row-info">
      <span class="lb-top-row-pseudo">
        {{ entry.display_name }}
        <span v-if="entry.is_current_user" class="lb-top-row-me-pill">
          {{ $t('portal.leaderboard.myRank.label') }}
        </span>
      </span>
      <span class="lb-top-row-title">
        {{ $t(`portal.profile.titles.${entry.title_key || 'spectator'}`) }}
      </span>
    </div>
    <span
      class="gc-lb-move lb-top-row-move"
      :class="moveClass(entry.movement)"
      :title="moveTooltip(entry.movement)"
    >
      <ChevronUp v-if="entry.movement > 0" :size="10" :stroke-width="3.5" />
      <ChevronDown v-else-if="entry.movement < 0" :size="10" :stroke-width="3.5" />
      <span v-else>—</span>
      <span v-if="entry.movement">{{ Math.abs(entry.movement) }}</span>
    </span>
    <span class="lb-top-row-xp">{{ (entry.month_xp || 0).toLocaleString() }} XP</span>
  </router-link>
</template>

<script setup>
import { useI18n } from 'vue-i18n'
import { ChevronDown, ChevronUp } from 'lucide-vue-next'

import MkAvatar from '@/components/common/MkAvatar.vue'

defineProps({
  entry: { type: Object, default: null },
  index: { type: Number, default: 0 },
})

const { t } = useI18n()
function moveClass(movement) {
  if (!movement) return 'gc-lb-move--flat'
  return movement > 0 ? 'gc-lb-move--up' : 'gc-lb-move--down'
}
function moveTooltip(movement) {
  if (!movement) return t('portal.profile.rankStable')
  const key = movement > 0 ? 'portal.profile.rankUp' : 'portal.profile.rankDown'
  return t(key, { n: Math.abs(movement) })
}
</script>

<style scoped>
.lb-top-row {
  display: grid;
  grid-template-columns: 36px 40px minmax(0, 1fr) auto 110px;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  min-height: 64px;
  border-radius: var(--portal-radius-md);
  background: var(--portal-surface-1);
  border: 1px solid rgb(255, 255, 255, 0.06);
  color: var(--portal-text-primary);
  text-decoration: none;
  transition:
    transform var(--portal-dur-base) var(--portal-ease-emphasis),
    box-shadow var(--portal-dur-base) var(--portal-ease-emphasis),
    border-color var(--portal-dur-base) var(--portal-ease-emphasis);
}
.lb-top-row--me {
  background: rgb(var(--accent-rgb), 0.08);
  border-left: 3px solid var(--accent-500);
}
@media (hover: hover) {
  .lb-top-row:hover {
    transform: translateY(-2px);
    box-shadow: var(--portal-shadow-accent);
  }
}
.lb-top-row-rank {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 4px 8px;
  border-radius: var(--portal-radius-pill);
  font-size: var(--portal-text-xs);
  font-weight: var(--portal-font-bold);
  background: var(--portal-surface-3);
  color: var(--portal-text-body);
  font-variant-numeric: tabular-nums;
  min-width: 36px;
}
.lb-top-row-rank--gold {
  background: rgb(var(--portal-color-warning-rgb), 0.18);
  color: var(--portal-color-warning);
}
.lb-top-row-rank--platinum {
  background: rgb(var(--portal-color-cinema-rgb), 0.18);
  color: var(--portal-color-cinema);
}
.lb-top-row-rank--diamond,
.lb-top-row-rank--master,
.lb-top-row-rank--legendary {
  background: rgb(var(--portal-color-premium-rgb), 0.18);
  color: var(--portal-color-premium);
}
.lb-top-row-av {
  width: 40px;
  height: 40px;
  padding: 2px;
}
.lb-top-row-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.lb-top-row-pseudo {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: var(--portal-text-base);
  font-weight: var(--portal-font-medium);
  color: var(--portal-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.lb-top-row-me-pill {
  font-size: var(--portal-text-3xs);
  font-weight: var(--portal-font-bold);
  text-transform: uppercase;
  letter-spacing: var(--portal-tracking-widest);
  padding: 2px 6px;
  border-radius: var(--portal-radius-pill);
  background: var(--accent-500);
  color: var(--portal-text-primary);
}
.lb-top-row-title {
  font-size: var(--portal-text-3xs);
  text-transform: uppercase;
  letter-spacing: var(--portal-tracking-caps);
  color: var(--portal-text-muted);
}
.lb-top-row-move {
  min-width: 36px;
}
.lb-top-row-xp {
  font-family: 'Roboto Mono', monospace;
  font-size: var(--portal-text-base);
  color: var(--accent);
  text-align: right;
  font-variant-numeric: tabular-nums;
}
@media (max-width: 640px) {
  .lb-top-row {
    grid-template-columns: 36px 36px minmax(0, 1fr) 90px;
    gap: 8px;
    padding: 8px 12px;
    min-height: 56px;
  }
  .lb-top-row-move {
    display: none;
  }
  .lb-top-row-av {
    width: 36px;
    height: 36px;
  }
}
</style>
