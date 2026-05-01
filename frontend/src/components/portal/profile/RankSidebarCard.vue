<template>
  <div class="gc-sidebar">
    <template v-if="rankTier === 'legendary'">
      <div class="gc-aurora" />
      <div class="gc-starfield"><span v-for="i in 15" :key="'s'+i" class="gc-star" /></div>
    </template>
    <div class="gc-sidebar-inner">
      <!-- Avatar zone -->
      <div class="gc-avatar-zone" :class="avatarEffectClass">
        <!-- Master avatar cosmetic overlays (one block per equipped effect) -->
        <template v-if="avatarEffect === 'dedication'">
          <div class="gc-fx-comet-core" />
          <div class="gc-fx-comet-trail" />
          <div class="gc-fx-comet-head" />
        </template>
        <template v-else-if="avatarEffect === 'special'">
          <div class="gc-fx-holy-rays" />
          <div class="gc-fx-holy-glow" />
          <div class="gc-fx-holy-ring" />
          <div class="gc-fx-rune" /><div class="gc-fx-rune" />
          <div class="gc-fx-rune" /><div class="gc-fx-rune" />
        </template>
        <template v-else-if="avatarEffect === 'community'">
          <div class="gc-fx-nebula" />
          <span v-for="i in 8" :key="'cstar'+i" class="gc-fx-star" />
        </template>
        <template v-else-if="avatarEffect === 'ranking'">
          <div v-for="i in 5" :key="'rhalo'+i" class="gc-fx-rhalo" :class="`gc-fx-rhalo--${i}`" />
        </template>
        <template v-else-if="avatarEffect === 'meta'">
          <div class="gc-fx-mandala gc-fx-mandala--dots" />
          <div class="gc-fx-mandala gc-fx-mandala--outer" />
          <div class="gc-fx-mandala gc-fx-mandala--mid" />
          <div class="gc-fx-mandala gc-fx-mandala--inner" />
        </template>

        <div class="gc-avatar-ring">
          <div class="gc-avatar-inner">
            <img
              v-if="profileData?.avatar_url"
              :src="profileData.avatar_url"
              :alt="profileData.display_name"
              class="gc-avatar-img"
            />
            <span v-else class="gc-avatar-letter">
              {{ profileData?.display_name?.charAt(0)?.toUpperCase() || '?' }}
            </span>
          </div>
        </div>

        <!-- Ranking stars render above the avatar — must be placed AFTER the
             avatar-ring so they're z-stacked on top with their orbit paths. -->
        <template v-if="avatarEffect === 'ranking'">
          <div v-for="i in 5" :key="'rstar'+i" class="gc-fx-rstar" :class="`gc-fx-rstar--${i}`" />
        </template>
      </div>

      <div class="gc-rank-title">✦ {{ $t(`portal.profile.titles.${titleKey}`) }} ✦</div>
      <h3 class="gc-name">{{ profileData?.display_name || $t('portal.profile.defaultUserName') }}</h3>
      <div v-if="profileData?.selected_title" class="gc-custom-title" :class="`gc-custom-title--${titleTierName}`">{{ $t(profileData.selected_title) }}</div>
      <div class="gc-level">{{ $t('portal.profile.level') }} {{ profileData?.level || 1 }}</div>

      <div class="gc-xp-wrap">
        <div class="gc-xp-track">
          <div class="gc-xp-fill" :style="{ width: xpPercent + '%' }" />
          <div class="gc-xp-shine" />
        </div>
        <span class="gc-xp-text">{{ Math.min(profileData?.xp || 0, nextLevelXp).toLocaleString() }} / {{ nextLevelXp.toLocaleString() }} XP</span>
      </div>

      <!-- Ranking detail block -->
      <div class="gc-ranking-block">
        <div class="gc-ranking-label">{{ $t('portal.profile.ranking') }}</div>
        <div class="gc-ranking-pos">#{{ ranking.position || '—' }}</div>
        <div
          v-if="ranking.movement > 0"
          class="gc-ranking-move gc-ranking-move--up"
        >+{{ ranking.movement }} {{ $t('portal.profile.places') }}</div>
        <div
          v-else-if="ranking.movement < 0"
          class="gc-ranking-move gc-ranking-move--down"
        >{{ ranking.movement }} {{ $t('portal.profile.places') }}</div>
        <div v-else class="gc-ranking-move gc-ranking-move--same">=</div>
        <div class="gc-ranking-pct-row">
          <div class="gc-ranking-pct-bar"><div class="gc-ranking-pct-fill" :style="{ width: (100 - (ranking.percentile || 50)) + '%' }" /></div>
        </div>
        <div class="gc-ranking-pct-text">Top {{ ranking.percentile || '—' }}%</div>
      </div>
      <div class="gc-member-since">
        {{ $t('portal.profile.memberSince', { months: memberSince }) }}
      </div>

      <div v-if="pinnedTrophies.length" class="gc-pinned">
        <div class="gc-pinned-label">{{ $t('portal.profile.pinnedBadges') || 'Pinned' }}</div>
        <div class="gc-pinned-row">
          <div v-for="t in pinnedTrophies" :key="t.id"
            class="gc-pinned-item"
            :class="`gc-pinned-item--rarity-${t.rarity}`"
            :title="$t(t.name_key)">
            <component :is="iconMap[t.icon] || HelpCircle" :size="16" />
          </div>
        </div>
      </div>

      <button class="gc-edit" @click="$emit('edit-profile')">
        {{ $t('portal.profile.editProfile') }}
      </button>
    </div>
    <!-- Particles -->
    <div class="gc-particles"><span v-for="i in 8" :key="'p'+i" class="gc-particle" /></div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { HelpCircle } from 'lucide-vue-next'

const props = defineProps({
  profileData: { type: Object, default: null },
  rankTier: { type: String, default: 'bronze' },
  titleKey: { type: String, default: 'spectator' },
  titleTierName: { type: String, default: 'mythic' },
  ranking: { type: Object, default: () => ({ position: 0, percentile: 0, movement: 0 }) },
  memberSince: { type: [Number, String], default: '—' },
  xpPercent: { type: Number, default: 0 },
  nextLevelXp: { type: Number, default: 100 },
  trophies: { type: Array, default: () => [] },
  iconMap: { type: Object, default: () => ({}) },
})

defineEmits(['edit-profile'])

const VALID_AVATAR_FX = new Set([
  'watching', 'dedication', 'diversity', 'special',
  'community', 'ranking', 'meta',
])
const avatarEffect = computed(() => {
  const raw = props.profileData?.avatar_effect
  return VALID_AVATAR_FX.has(raw) ? raw : null
})
const avatarEffectClass = computed(() =>
  avatarEffect.value ? `gc-avatar-fx--${avatarEffect.value}` : '',
)

const pinnedTrophies = computed(() => {
  const ids = props.profileData?.selected_badges || []
  if (!ids.length) return []
  return ids
    .map(id => props.trophies.find(t => t.id === id))
    .filter(Boolean)
})
</script>

<style>
@import '@/assets/styles/portal/rank-card.css';
@import '@/assets/styles/portal/trophy-master-avatar-fx.css';
</style>
