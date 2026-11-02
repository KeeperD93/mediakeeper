<template>
  <div v-if="entries.length || widget" class="gc-lb-box" :class="{ 'gc-lb-box--widget': widget }">
    <router-link
      :to="{ name: 'portal-leaderboard' }"
      class="gc-box-title gc-box-title--link"
      :class="{ 'gc-lb-widget-title': widget }"
      :title="$t('portal.profile.viewFullLeaderboard')"
    >
      {{ $t('portal.profile.ranking') }}
      <ChevronRight :size="14" :stroke-width="2.5" class="gc-box-title-chevron" />
    </router-link>
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
        <div class="gc-lb-av">
          <MkAvatar
            :name="entry.display_name || ''"
            :src="entry.avatar_url || null"
            :size="28"
            :tier="entry.tier || 'bronze'"
            class="gc-lb-av-mk"
          />
        </div>
        <div class="gc-lb-info">
          <span class="gc-lb-n">{{ entry.display_name }}</span>
          <span class="gc-lb-tier">
            <LeaderboardLevelTitle :entry="entry" />
          </span>
        </div>
        <span class="gc-lb-figures">
          <LeaderboardTrophies :count="entry.trophies_won" />
          <LeaderboardMove :movement="entry.movement" />
          <span class="gc-lb-v">{{ (entry.period_xp || 0).toLocaleString() }} XP</span>
        </span>
      </component>
    </div>
  </div>
</template>

<script setup>
import { ChevronRight } from 'lucide-vue-next'
import MkAvatar from '@/components/common/MkAvatar.vue'
import LeaderboardLevelTitle from '@/components/portal/leaderboard/LeaderboardLevelTitle.vue'
import LeaderboardMove from '@/components/portal/leaderboard/LeaderboardMove.vue'
import LeaderboardTrophies from '@/components/portal/leaderboard/LeaderboardTrophies.vue'

defineProps({
  entries: { type: Array, default: () => [] },
  widget: { type: Boolean, default: false },
})
</script>

<style>
@import url('@/assets/styles/portal/leaderboard-card.css');
</style>
