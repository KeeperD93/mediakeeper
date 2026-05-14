<template>
  <router-link
    v-if="entry"
    :to="{ name: 'portal-user-profile', params: { id: entry.user_id } }"
    class="lb-hero"
    :aria-label="$t('portal.leaderboard.hero.rankBadge')"
  >
    <div class="lb-hero-avatar" :class="`lb-hero-avatar--${entry.tier || 'gold'}`">
      <div class="lb-hero-avatar-inner">
        <MkAvatar
          :name="entry.display_name || ''"
          :src="entry.avatar_url || null"
          :size="140"
        />
      </div>
    </div>

    <div class="lb-hero-body">
      <div class="lb-hero-rank">
        <span class="lb-hero-rank-num">#1</span>
        <Crown :size="32" :stroke-width="2.5" class="lb-hero-crown" aria-hidden="true" />
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
            entry.title_tier
              ? `lb-hero-custom-title--rarity-${tierToRarity(entry.title_tier)}`
              : ''
          "
        >
          · {{ $t(entry.selected_title) }}
        </em>
      </div>
      <div class="lb-hero-xp">
        <span class="lb-hero-xp-value">{{ displayedXp.toLocaleString() }}</span>
        <span class="lb-hero-xp-unit">XP</span>
      </div>
      <div v-if="leadOver2 > 0" class="lb-hero-lead">
        <Trophy :size="14" :stroke-width="2.5" aria-hidden="true" />
        {{ $t('portal.leaderboard.hero.leadOverSecond', { n: leadOver2.toLocaleString() }) }}
      </div>
    </div>
  </router-link>
</template>

<script setup>
import { computed, toRef } from 'vue'
import { Crown, Trophy } from 'lucide-vue-next'

import MkAvatar from '@/components/common/MkAvatar.vue'
import { useCountUp } from '@/composables/portal/useCountUp'

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
const targetXp = computed(() => entryRef.value?.month_xp || 0)
const leadOver2 = computed(() => Math.max(0, entryRef.value?.lead_over_2 || 0))

const { displayed: displayedXp } = useCountUp(targetXp.value, { duration: 1400 })
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
  background:
    radial-gradient(ellipse at center, rgb(var(--portal-color-warning-rgb), 0.18) 0%, transparent 70%),
    var(--portal-surface-2);
  border: 1px solid rgb(var(--portal-color-warning-rgb), 0.35);
  box-shadow: 0 8px 30px rgb(var(--portal-color-warning-rgb), 0.12);
  position: relative;
  overflow: hidden;
}
.lb-hero::after {
  content: '';
  position: absolute;
  inset: 0;
  background: radial-gradient(ellipse at center, transparent 55%, rgb(0, 0, 0, 0.32));
  pointer-events: none;
}
.lb-hero-avatar {
  width: 140px;
  height: 140px;
  flex-shrink: 0;
  border-radius: var(--portal-radius-circle);
  /* Ring drawn by MkAvatar's CSS border — pure layout container here.
     Default ring colour is rank-1 gold; tier variants override below
     so a top-rank user in a different tier (e.g. legendary) still gets
     their own tier colour rather than a hard-coded gold ring. */
  --mk-avatar-ring-width: 5px;
  --mk-avatar-ring-color: var(--portal-color-warning);
  position: relative;
  z-index: 1;
}
.lb-hero-avatar--bronze {
  --mk-avatar-ring-color: #cd7f32;
}
.lb-hero-avatar--silver {
  --mk-avatar-ring-color: #c0c0c0;
}
.lb-hero-avatar--gold {
  --mk-avatar-ring-color: var(--portal-color-warning);
}
.lb-hero-avatar--platinum {
  --mk-avatar-ring-color: var(--portal-color-cinema);
}
.lb-hero-avatar--diamond {
  --mk-avatar-ring-color: #7c3aed;
}
.lb-hero-avatar--master {
  --mk-avatar-ring-color: var(--portal-color-error);
}
.lb-hero-avatar--legendary {
  --mk-avatar-ring-color: var(--portal-color-warning);
}
.lb-hero-avatar-inner {
  width: 100%;
  height: 100%;
  border-radius: var(--portal-radius-circle);
  /* Transparent so the page bg shows through the hollow ring above. */
  background: transparent;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}
.lb-hero-body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
  position: relative;
  z-index: 1;
}
.lb-hero-rank {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  position: relative;
}
.lb-hero-rank-num {
  font-family: var(--portal-font-display);
  font-weight: var(--portal-font-black);
  font-size: clamp(4rem, 8vw, 6rem);
  line-height: 1;
  color: var(--portal-color-warning);
  text-shadow: 0 4px 24px rgb(var(--portal-color-warning-rgb), 0.45);
  letter-spacing: var(--portal-tracking-tight);
}
.lb-hero-crown {
  color: var(--portal-color-warning);
  filter: drop-shadow(0 2px 4px rgb(0, 0, 0, 0.3));
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
.lb-hero-lead {
  align-self: flex-start;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  border-radius: var(--portal-radius-pill);
  background: rgb(var(--portal-color-success-rgb), 0.18);
  color: var(--portal-color-success);
  font-size: var(--portal-text-xs);
  font-weight: var(--portal-font-bold);
  margin-top: 4px;
}
@media (max-width: 640px) {
  .lb-hero {
    gap: 16px;
    padding: 18px;
    min-height: 240px;
  }
  .lb-hero-avatar {
    width: 96px;
    height: 96px;
  }
}
.lb-hero-custom-title--rarity-common { color: var(--portal-text-body); }
.lb-hero-custom-title--rarity-uncommon { color: var(--portal-color-success); }
.lb-hero-custom-title--rarity-rare { color: var(--portal-color-cinema); }
.lb-hero-custom-title--rarity-epic { color: var(--portal-color-premium); }
.lb-hero-custom-title--rarity-legendary { color: var(--portal-color-warning); }
.lb-hero-custom-title--rarity-mythic { color: var(--portal-color-error); }
</style>
