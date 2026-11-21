<template>
  <div class="gc-sidebar">
    <template v-if="rankTier === 'legendary'">
      <div class="gc-aurora" />
      <div class="gc-starfield"><span v-for="i in 15" :key="'s' + i" class="gc-star" /></div>
    </template>
    <div class="gc-sidebar-inner">
      <!-- Avatar zone: the frame of a Master trophy around the tier ring. -->
      <div class="gc-avatar-zone">
        <AvatarFrame :size="88" :effect="profileData?.avatar_effect" reserve>
          <div class="gc-avatar-ring">
            <div class="gc-avatar-inner">
              <MkAvatar
                :name="profileData?.display_name || ''"
                :src="profileData?.avatar_url || null"
                :size="88"
                class="gc-avatar-mk"
              />
            </div>
          </div>
        </AvatarFrame>
      </div>

      <div class="gc-rank-title">✦ {{ $t(`portal.profile.titles.${titleKey}`) }} ✦</div>
      <h3 class="gc-name">
        {{ profileData?.display_name || $t('portal.profile.defaultUserName') }}
      </h3>
      <div
        v-if="profileData?.selected_title"
        class="gc-custom-title"
        :class="`gc-custom-title--${titleTierName}`"
      >
        {{ $t(profileData.selected_title) }}
      </div>
      <div class="gc-level">{{ $t('portal.profile.level') }} {{ profileData?.level || 1 }}</div>

      <div class="gc-xp-wrap">
        <div class="gc-xp-track">
          <div class="gc-xp-fill" :style="{ width: xpPercent + '%' }" />
          <div class="gc-xp-shine" />
        </div>
        <span class="gc-xp-text">
          {{ localizedNumber(Math.min(profileData?.xp || 0, nextLevelXp)) }} /
          {{ localizedNumber(nextLevelXp) }} XP
        </span>
      </div>

      <!-- Ranking detail block -->
      <div class="gc-ranking-block">
        <div class="gc-ranking-label">{{ $t('portal.profile.ranking') }}</div>
        <div class="gc-ranking-pos">#{{ ranking.position || '—' }}</div>
        <template v-if="ranking.position">
          <div v-if="ranking.movement > 0" class="gc-ranking-move gc-ranking-move--up">
            +{{ ranking.movement }} {{ $t('portal.profile.places') }}
          </div>
          <div v-else-if="ranking.movement < 0" class="gc-ranking-move gc-ranking-move--down">
            {{ ranking.movement }} {{ $t('portal.profile.places') }}
          </div>
          <div v-else class="gc-ranking-move gc-ranking-move--same">=</div>
          <div class="gc-ranking-pct-row">
            <div class="gc-ranking-pct-bar">
              <div class="gc-ranking-pct-fill" :style="{ width: 100 - ranking.percentile + '%' }" />
            </div>
          </div>
          <div class="gc-ranking-pct-text">
            {{ $t('portal.profile.topPercent', { percent: ranking.percentile }) }}
          </div>
        </template>
      </div>
      <div class="gc-member-since">
        {{ $t('portal.profile.memberSince', { months: memberSince }) }}
      </div>

      <div v-if="pinnedTrophies.length" class="gc-pinned">
        <div class="gc-pinned-label">{{ $t('portal.profile.pinnedBadges') || 'Pinned' }}</div>
        <div class="gc-pinned-row">
          <div
            v-for="t in pinnedTrophies"
            :key="t.id"
            class="gc-pinned-item"
            :class="`gc-pinned-item--rarity-${t.rarity}`"
            :title="$t(t.name_key)"
          >
            <component :is="iconMap[t.icon] || HelpCircle" :size="16" />
          </div>
        </div>
      </div>

      <button class="gc-edit" @click="$emit('edit-profile')">
        {{ $t('portal.profile.editProfile') }}
      </button>
    </div>
    <!-- Particles -->
    <div class="gc-particles"><span v-for="i in 8" :key="'p' + i" class="gc-particle" /></div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { HelpCircle } from 'lucide-vue-next'
import MkAvatar from '@/components/common/MkAvatar.vue'
import AvatarFrame from '@/components/portal/common/AvatarFrame.vue'
import { xpForLevel } from '@/composables/portal/useProfileXp'
import { MIN_LEVEL } from '@/constants/portal'
import { localizedNumber } from '@/utils/localizedNumber'

const props = defineProps({
  profileData: { type: Object, default: null },
  rankTier: { type: String, default: 'bronze' },
  titleKey: { type: String, default: 'spectator' },
  titleTierName: { type: String, default: 'mythic' },
  ranking: { type: Object, default: () => ({ position: 0, percentile: 0, movement: 0 }) },
  memberSince: { type: [Number, String], default: '—' },
  xpPercent: { type: Number, default: 0 },
  nextLevelXp: { type: Number, default: xpForLevel(MIN_LEVEL + 1) },
  trophies: { type: Array, default: () => [] },
  iconMap: { type: Object, default: () => ({}) },
})

defineEmits(['edit-profile'])

const pinnedTrophies = computed(() => {
  const ids = props.profileData?.selected_badges || []
  if (!ids.length) return []
  return ids.map(id => props.trophies.find(t => t.id === id)).filter(Boolean)
})
</script>

<style>
@import url('@/assets/styles/portal/rank-card.css');
</style>
