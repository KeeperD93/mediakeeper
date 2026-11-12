<template>
  <router-link
    v-if="entry"
    :to="{ name: 'portal-user-profile', params: { id: entry.user_id } }"
    class="lb-hero lb-metal lb-metal--gold"
  >
    <Crown :size="32" :stroke-width="2.5" class="lb-hero-crown" aria-hidden="true" />
    <div class="lb-hero-avatar">
      <div class="lb-hero-avatar-inner">
        <MkAvatar
          :name="entry.display_name || ''"
          :src="entry.avatar_url || null"
          :size="140"
          :tier="entry.tier || 'gold'"
        />
      </div>
    </div>

    <div class="lb-hero-body">
      <div class="lb-hero-rank">
        <span class="lb-hero-rank-num lb-metal-digits">#1</span>
        <LeaderboardMePill v-if="entry.is_current_user" />
      </div>
      <div class="lb-hero-name">{{ entry.display_name }}</div>
      <div class="lb-hero-meta">
        {{
          $t('portal.leaderboard.hero.levelTitle', {
            level: entry.level,
            title: $t(`portal.profile.titles.${entry.title_key || 'spectator'}`),
          })
        }}
        <em
          v-if="entry.selected_title"
          class="lb-hero-custom-title"
          :class="
            entry.title_tier ? `lb-hero-custom-title--rarity-${tierToRarity(entry.title_tier)}` : ''
          "
        >
          · {{ $t(entry.selected_title) }}
        </em>
      </div>
      <div class="lb-hero-xp">
        <span class="lb-hero-xp-value">{{ localizedNumber(displayedXp) }}</span>
        <span class="lb-hero-xp-unit">XP</span>
      </div>
      <div v-if="leadOver2 > 0 || entry.trophies_won > 0" class="lb-hero-chips">
        <div v-if="leadOver2 > 0" class="lb-hero-lead">
          {{ $t('portal.leaderboard.hero.leadOverSecond', { n: localizedNumber(leadOver2) }) }}
        </div>
        <LeaderboardTrophies :count="entry.trophies_won" large />
      </div>
    </div>
  </router-link>
</template>

<script setup>
import { computed, toRef } from 'vue'
import { Crown } from 'lucide-vue-next'

import MkAvatar from '@/components/common/MkAvatar.vue'
import LeaderboardMePill from '@/components/portal/leaderboard/LeaderboardMePill.vue'
import LeaderboardTrophies from '@/components/portal/leaderboard/LeaderboardTrophies.vue'
import { useCountUp } from '@/composables/portal/useCountUp'
import { localizedNumber } from '@/utils/localizedNumber'

const props = defineProps({
  entry: { type: Object, default: null },
})

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

const entryRef = toRef(props, 'entry')
const targetXp = computed(() => entryRef.value?.period_xp || 0)
const leadOver2 = computed(() => Math.max(0, entryRef.value?.lead_over_2 || 0))

const { displayed: displayedXp } = useCountUp(targetXp, { duration: 1400 })
</script>

<style scoped>
.lb-hero {
  display: flex;
  align-items: center;
  gap: 24px;
  padding: 24px 28px;
  min-height: 240px;
  border-radius: var(--portal-radius-lg);
  text-decoration: none;
  color: var(--portal-text-primary);
  position: relative;
  overflow: hidden;
}
.lb-hero-avatar {
  width: 140px;
  height: 140px;
  flex-shrink: 0;
  border-radius: var(--portal-radius-circle);
  /* Pure layout container — the tier ring (colour, halo, and the
     spinning legendary rainbow) is drawn by MkAvatar itself via the
     universal :tier prop, so the #1 champion matches every other
     leaderboard surface instead of a static bespoke ring. */
}
.lb-hero-avatar-inner {
  width: 100%;
  height: 100%;
  border-radius: var(--portal-radius-circle);
  /* Transparent so the page bg shows through MkAvatar's hollow tier
     ring (the ring is a border on MkAvatar itself). */
  background: transparent;
  display: flex;
  align-items: center;
  justify-content: center;
}
/* The champion avatar is much larger (140px) than the podium (84px), so the
   universal 2px ring reads as too thin here. Match the podium's visual ring
   weight with a proportionally thicker 5px ring (5px / 140px ≈ 3px / 84px).
   Mirrors the podium's :deep override; legendary keeps its rainbow ::after
   but widens its band to the same 5px. */
.lb-hero-avatar :deep(.mk-avatar:not(.mk-avatar-tier--legendary)) {
  --mk-avatar-ring-width: 5px;
}
.lb-hero-avatar :deep(.mk-avatar-tier--legendary)::after {
  padding: 5px;
}
.lb-hero-body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.lb-hero-rank {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
.lb-hero-rank-num {
  font-family: var(--portal-font-display);
  font-weight: var(--portal-font-black);
  font-size: clamp(4rem, 8vw, 6rem);
  line-height: 1;
  letter-spacing: var(--portal-tracking-tight);
}
.lb-hero-crown {
  position: absolute;
  top: var(--portal-space-3);
  right: var(--portal-space-3);
  color: var(--portal-color-warning);
}
.lb-hero-name {
  font-size: clamp(1.5rem, 3vw, 2rem);
  font-weight: var(--portal-font-extrabold);
  color: var(--portal-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.lb-hero-meta {
  font-size: var(--portal-text-xs);
  color: var(--portal-text-muted);
  text-transform: uppercase;
  letter-spacing: var(--portal-tracking-caps);
  opacity: 0.85;
}
.lb-hero-custom-title {
  font-style: italic;
  color: var(--accent);
}
.lb-hero-xp {
  display: inline-flex;
  align-items: baseline;
  gap: 6px;
  margin-top: 4px;
}
.lb-hero-xp-value {
  font-family: var(--portal-font-display);
  font-weight: var(--portal-font-black);
  font-size: clamp(2.5rem, 5vw, 3.5rem);
  line-height: 1;
  color: var(--portal-color-warning);
}
.lb-hero-xp-unit {
  font-family: var(--portal-font-display);
  font-weight: var(--portal-font-bold);
  font-size: var(--portal-text-xl);
  color: var(--portal-color-warning);
  opacity: 0.85;
}
.lb-hero-chips {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  margin-top: 4px;
}
/* The bubble overhangs on the left: its "+" falls under the first digit of the XP. */
.lb-hero-lead {
  --lb-lead-side: var(--portal-space-3);

  margin-left: calc(-1 * var(--lb-lead-side));
  padding: var(--portal-space-1) var(--lb-lead-side);
  border-radius: var(--portal-radius-pill);
  background: rgb(var(--portal-color-success-rgb), 0.18);
  color: var(--portal-color-success);
  font-size: var(--portal-text-xs);
  font-weight: var(--portal-font-bold);
}
@media (max-width: 640px) {
  /* A compact banner on a phone: the ranking must start within the first screen. */
  .lb-hero {
    gap: 12px;
    padding: 12px 14px;
    min-height: 0;
  }
  .lb-hero-avatar {
    width: 64px;
    height: 64px;
  }
  /* Scale the fixed 140 px MkAvatar into the smaller slot: cropping it would
     cut its tier ring and halo. */
  .lb-hero-avatar :deep(.mk-avatar) {
    flex-shrink: 0;
    transform: scale(calc(64 / 140));
  }
  .lb-hero-body {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr);
    align-items: center;
    gap: 2px 8px;
  }
  .lb-hero-meta,
  .lb-hero-xp,
  .lb-hero-chips {
    grid-column: 1 / -1;
  }
  .lb-hero-rank-num {
    font-size: var(--portal-text-2xl);
  }
  .lb-hero-crown {
    top: var(--portal-space-2);
    right: var(--portal-space-2);
    width: 18px;
    height: 18px;
  }
  /* The name shares its line with the crown: a long one stops before it. */
  .lb-hero-name {
    padding-right: 20px;
    font-size: var(--portal-text-md);
  }
  .lb-hero-meta {
    font-size: var(--portal-text-3xs);
  }
  .lb-hero-xp-value {
    font-size: var(--portal-text-xl);
  }
  .lb-hero-xp-unit {
    font-size: var(--portal-text-sm);
  }
  .lb-hero-chips {
    margin-top: 2px;
  }
  .lb-hero-lead {
    --lb-lead-side: var(--portal-space-2);

    padding-block: var(--portal-space-0-5);
    font-size: var(--portal-text-3xs);
  }
}
.lb-hero-custom-title--rarity-common {
  color: var(--portal-text-body);
}
.lb-hero-custom-title--rarity-uncommon {
  color: var(--portal-color-success);
}
.lb-hero-custom-title--rarity-rare {
  color: var(--portal-color-cinema);
}
.lb-hero-custom-title--rarity-epic {
  color: var(--portal-color-premium);
}
.lb-hero-custom-title--rarity-legendary {
  color: var(--portal-color-warning);
}
.lb-hero-custom-title--rarity-mythic {
  color: var(--portal-color-error);
}
</style>
