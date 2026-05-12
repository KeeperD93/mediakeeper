<template>
  <div v-if="entries.length || widget" class="gc-lb-box" :class="{ 'gc-lb-box--widget': widget }">
    <h4 class="gc-box-title" :class="{ 'gc-lb-widget-title': widget }">
      {{ $t('portal.profile.ranking') }}
    </h4>
    <div class="gc-lb-rows" :data-full="entries.length >= 16 || null">
      <component
        :is="entry.user_id ? 'router-link' : 'div'"
        v-for="entry in entries"
        :key="entry.rank"
        :to="
          entry.user_id ? { name: 'portal-user-profile', params: { id: entry.user_id } } : undefined
        "
        class="gc-lb-row"
        :class="{
          ['gc-lb-row--' + entry.rank]: entry.rank <= 3,
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
            class="gc-lb-av-mk"
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

<script setup>
import { useI18n } from 'vue-i18n'
import { ChevronDown, ChevronUp } from 'lucide-vue-next'
import MkAvatar from '@/components/common/MkAvatar.vue'

defineProps({
  entries: { type: Array, default: () => [] },
  widget: { type: Boolean, default: false },
})

const { t } = useI18n()

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
</script>

<style>
@import url('@/assets/styles/portal/leaderboard-card.css');
</style>
