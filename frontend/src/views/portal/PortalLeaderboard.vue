<template>
  <div class="pt-leaderboard mk-page-root">
    <header class="pt-lb-header">
      <h1>{{ $t('portal.leaderboard.title') }}</h1>
      <p class="pt-lb-subtitle">
        {{ $t('portal.leaderboard.subtitle', { n: entries.length || 0 }) }}
      </p>
    </header>

    <p v-if="loading" class="pt-lb-state">{{ $t('common.loading') }}</p>

    <p v-else-if="!entries.length" class="pt-lb-state">
      {{ $t('portal.leaderboard.emptyState') }}
    </p>

    <template v-else>
      <PortalLeaderboardPodium :entries="podium" />

      <div class="pt-lb-rest">
        <div class="gc-lb-rows">
          <component
            :is="entry.user_id ? 'router-link' : 'div'"
            v-for="entry in rest"
            :key="entry.rank"
            :to="
              entry.user_id
                ? { name: 'portal-user-profile', params: { id: entry.user_id } }
                : undefined
            "
            class="gc-lb-row"
            :class="{
              'gc-lb-row--me': entry.is_current_user,
              'gc-lb-row--linkable': !!entry.user_id,
            }"
          >
            <span class="gc-lb-pos">{{ entry.rank }}</span>
            <div class="gc-lb-av" :class="`gc-lb-av--${entry.tier || 'bronze'}`">
              <MkAvatar
                :name="entry.display_name || ''"
                :src="entry.avatar_url || null"
                :size="24"
              />
            </div>
            <div class="gc-lb-info">
              <span class="gc-lb-n">{{ entry.display_name }}</span>
              <span class="gc-lb-tier">
                {{ $t(`portal.profile.titles.${entry.title_key || 'spectator'}`) }}
                <em
                  v-if="entry.selected_title"
                  class="gc-lb-custom-title"
                  :class="
                    entry.title_tier
                      ? `gc-lb-custom-title--rarity-${tierToRarity(entry.title_tier)}`
                      : ''
                  "
                >
                  · {{ $t(entry.selected_title) }}
                </em>
              </span>
            </div>
            <span
              class="gc-lb-move"
              :class="moveClass(entry.movement)"
              :title="moveTooltip(entry.movement)"
            >
              <ChevronUp v-if="entry.movement > 0" :size="9" :stroke-width="3.5" />
              <ChevronDown v-else-if="entry.movement < 0" :size="9" :stroke-width="3.5" />
              <span v-else>—</span>
              <span v-if="entry.movement">{{ Math.abs(entry.movement) }}</span>
            </span>
            <span class="gc-lb-v">{{ (entry.month_xp || 0).toLocaleString() }} XP</span>
          </component>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { ChevronDown, ChevronUp } from 'lucide-vue-next'

import MkAvatar from '@/components/common/MkAvatar.vue'
import PortalLeaderboardPodium from '@/components/portal/leaderboard/PortalLeaderboardPodium.vue'
import { useMonthlyLeaderboard } from '@/composables/portal/useMonthlyLeaderboard'

const { t } = useI18n()
const { entries, loading, fetchTop } = useMonthlyLeaderboard()

const podium = computed(() => entries.value.slice(0, 3))
const rest = computed(() => entries.value.slice(3))

const RARITY_BY_TIER = {
  1: 'common',
  2: 'uncommon',
  3: 'rare',
  4: 'epic',
  5: 'legendary',
  6: 'mythic',
}
function tierToRarity(tier) {
  return RARITY_BY_TIER[tier] || 'common'
}
function moveClass(movement) {
  if (!movement) return 'gc-lb-move--flat'
  return movement > 0 ? 'gc-lb-move--up' : 'gc-lb-move--down'
}
function moveTooltip(movement) {
  if (!movement) return t('portal.profile.rankStable')
  const key = movement > 0 ? 'portal.profile.rankUp' : 'portal.profile.rankDown'
  return t(key, { n: Math.abs(movement) })
}

onMounted(() => fetchTop(100))
</script>

<style scoped>
.pt-leaderboard {
  max-width: 960px;
  margin: 0 auto;
  padding: 1.5rem;
}
.pt-lb-header {
  margin-bottom: 1.75rem;
}
.pt-lb-header h1 {
  font-size: var(--portal-text-xl);
  font-weight: var(--portal-font-extrabold);
  color: var(--text-primary);
  margin: 0;
}
.pt-lb-subtitle {
  margin-top: 0.25rem;
  font-size: var(--portal-text-xs);
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: var(--portal-tracking-caps);
}
.pt-lb-state {
  text-align: center;
  color: var(--text-muted);
  padding: 2.5rem 1rem;
}
.pt-lb-rest {
  background: var(--portal-surface-1);
  border: 1px solid rgb(255, 255, 255, 0.05);
  border-radius: var(--radius-card);
  padding: 0.85rem;
}
</style>

<style>
/* The .gc-lb-* classes used by ranks 4-100 live in the global
   leaderboard-card stylesheet — single source of truth for rank-tier
   gradients and movement-arrow styling, shared with the profile mini
   leaderboard. */
@import url('@/assets/styles/portal/leaderboard-card.css');
</style>
