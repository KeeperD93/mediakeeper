<template>
  <aside class="pt-settings-hero">
    <!-- Mirror of /portal/me: the RankSidebarCard is wrapped in the
         same `.gc.gc--{tier}` container so the tier-driven FX (aurora,
         starfield, particles, ring shimmer…) render the same way here
         as on the profile dashboard. The tier class is gated on a
         truthy `rankTier`: while the profile loads (~0.5s) the card
         shows a neutral skeleton instead of flashing the bronze
         level-1 theme on a higher-tier user. -->
    <section class="gc" :class="rankTier ? `gc--${rankTier}` : ''">
      <RankSidebarCard
        :profile-data="livePreviewProfile"
        :rank-tier="rankTier"
        :title-key="titleKey"
        :title-tier-name="titleTierName"
        :ranking="ranking"
        :member-since="memberSince"
        :xp-percent="xpPercent"
        :next-level-xp="nextLevelXp"
        :trophies="trophies"
        :icon-map="iconMap"
        @edit-profile="() => {}"
      />
    </section>

    <div class="pt-settings-hero-actions">
      <span v-if="streakDays > 0" class="pt-settings-hero-streak">
        <Flame :size="14" />
        {{ $t('portal.settings.streak', { n: streakDays }) }}
      </span>
      <router-link
        v-if="profileData?.user_id"
        :to="{
          name: 'portal-user-profile',
          params: { id: profileData.user_id },
          query: { preview: 1 },
        }"
        class="pt-settings-btn"
      >
        <Eye :size="14" />
        {{ $t('portal.settings.viewAsOthers') }}
      </router-link>
    </div>
  </aside>
</template>

<script setup>
import { computed } from 'vue'
import { Eye, Flame } from 'lucide-vue-next'

import RankSidebarCard from '@/components/portal/profile/RankSidebarCard.vue'

const props = defineProps({
  profileData: { type: Object, default: null },
  livePreview: { type: Object, default: null },
  rankTier: { type: String, default: 'bronze' },
  titleKey: { type: String, default: 'spectator' },
  titleTierName: { type: String, default: 'mythic' },
  ranking: { type: Object, default: () => ({ position: 0, percentile: 0, movement: 0 }) },
  memberSince: { type: [Number, String], default: '—' },
  xpPercent: { type: Number, default: 0 },
  nextLevelXp: { type: Number, default: 100 },
  trophies: { type: Array, default: () => [] },
  iconMap: { type: Object, default: () => ({}) },
  streakDays: { type: Number, default: 0 },
})

// Live preview merges the form draft on top of the persisted profile so
// the RankCard reflects unsaved title / cosmetic / avatar changes.
const livePreviewProfile = computed(() => ({
  ...(props.profileData || {}),
  ...(props.livePreview || {}),
}))
</script>
