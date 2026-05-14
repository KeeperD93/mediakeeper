<template>
  <div class="pt-leaderboard mk-page-root">
    <div class="lb-particles" aria-hidden="true">
      <span
        v-for="particle in particles"
        :key="particle.id"
        class="lb-particle"
        :style="particle.style"
      />
    </div>

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
      <Transition name="lb-fade" appear>
        <div v-if="hero" id="lb-hero">
          <LeaderboardHeroBillboard :entry="hero" />
        </div>
      </Transition>

      <Transition name="lb-fade" appear>
        <LeaderboardStatsBar v-if="stats" :stats="stats" />
      </Transition>

      <Transition name="lb-fade" appear>
        <div v-if="podium.length" id="lb-podium">
          <PortalLeaderboardPodium :entries="podium" />
        </div>
      </Transition>

      <Transition name="lb-fade" appear>
        <LeaderboardMyRankCard
          v-if="myRankProps"
          :viewer-rank="myRankProps.viewerRank"
          :viewer-entry="myRankProps.viewerEntry"
          :in-list-entry="myRankProps.inListEntry"
          :stats="stats"
        />
      </Transition>

      <Transition name="lb-fade" appear>
        <div v-if="topTen.length" class="lb-top-ten">
          <h2 class="lb-section-title">{{ $t('portal.leaderboard.topTen') }}</h2>
          <LeaderboardTopTenRow
            v-for="(entry, idx) in topTen"
            :key="entry.rank"
            :entry="entry"
            :index="idx"
          />
        </div>
      </Transition>

      <Transition name="lb-fade" appear>
        <div v-if="rest.length" class="lb-rest">
          <h2 class="lb-section-title">{{ $t('portal.leaderboard.rest') }}</h2>
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
      </Transition>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { ChevronDown, ChevronUp } from 'lucide-vue-next'

import MkAvatar from '@/components/common/MkAvatar.vue'
import LeaderboardHeroBillboard from '@/components/portal/leaderboard/LeaderboardHeroBillboard.vue'
import LeaderboardStatsBar from '@/components/portal/leaderboard/LeaderboardStatsBar.vue'
import PortalLeaderboardPodium from '@/components/portal/leaderboard/PortalLeaderboardPodium.vue'
import LeaderboardMyRankCard from '@/components/portal/leaderboard/LeaderboardMyRankCard.vue'
import LeaderboardTopTenRow from '@/components/portal/leaderboard/LeaderboardTopTenRow.vue'
import { useMonthlyLeaderboard } from '@/composables/portal/useMonthlyLeaderboard'

const { t } = useI18n()
const { entries, stats, viewerRank, viewerEntry, loading, fetchTop } = useMonthlyLeaderboard()

const hero = computed(() => {
  const head = entries.value[0]
  if (!head) return null
  const second = entries.value[1]
  return {
    ...head,
    lead_over_2: second ? (head.month_xp || 0) - (second.month_xp || 0) : 0,
  }
})

const podium = computed(() => entries.value.slice(1, 3))
const topTen = computed(() => entries.value.slice(3, 13))
const rest = computed(() => entries.value.slice(13))

const inListEntry = computed(() => entries.value.find(e => e.is_current_user) || null)
const myRankProps = computed(() => {
  if (inListEntry.value) {
    return { viewerRank: null, viewerEntry: null, inListEntry: inListEntry.value }
  }
  if (viewerEntry.value && viewerRank.value) {
    return {
      viewerRank: viewerRank.value,
      viewerEntry: viewerEntry.value,
      inListEntry: null,
    }
  }
  return null
})

const particles = computed(() => {
  return Array.from({ length: 20 }, (_, i) => ({
    id: i,
    style: {
      left: `${(i * 53) % 100}%`,
      animationDelay: `${(i * 1.7) % 20}s`,
      animationDuration: `${15 + ((i * 7) % 10)}s`,
    },
  }))
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

<style>
@import url('@/assets/styles/portal/leaderboard-card.css');
@import url('@/assets/styles/portal/leaderboard-page.css');
</style>
