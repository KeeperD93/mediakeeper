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
      <h1>{{ $t(`portal.leaderboard.title.${period}`) }}</h1>
      <LeaderboardPeriodTabs v-model="period" :base-id="baseId" />
      <p class="pt-lb-subtitle">
        {{ $t('portal.leaderboard.subtitle', { n: entries.length }, entries.length) }}
      </p>
      <p class="pt-lb-note">{{ $t(`portal.leaderboard.scoringNote.${period}`) }}</p>
      <button v-if="myRestEntry" type="button" class="pt-lb-my-place" @click="scrollToMyRow">
        {{ $t('portal.leaderboard.myRank.seeMyPlace', { rank: myRestEntry.rank }) }}
        <ChevronDown :size="14" :stroke-width="2.5" aria-hidden="true" />
      </button>
    </header>

    <div :id="`${baseId}-panel`" role="tabpanel" :aria-labelledby="`${baseId}-tab-${period}`">
      <p v-if="loading" class="pt-lb-state">{{ $t('common.loading') }}</p>

      <p v-else-if="!entries.length" class="pt-lb-state">
        {{ $t(`portal.leaderboard.emptyState.${period}`) }}
      </p>

      <template v-else>
        <Transition name="lb-fade" appear>
          <div v-if="hero">
            <LeaderboardHeroBillboard :key="period" :entry="hero" />
          </div>
        </Transition>

        <Transition name="lb-fade" appear>
          <LeaderboardStatsBar v-if="stats" :key="period" :stats="stats" />
        </Transition>

        <Transition name="lb-fade" appear>
          <div v-if="podium.length">
            <PortalLeaderboardPodium :entries="podium" :period="period" />
          </div>
        </Transition>

        <Transition name="lb-fade" appear>
          <LeaderboardMyRankCard
            v-if="viewerRank && viewerEntry"
            :viewer-rank="viewerRank"
            :viewer-entry="viewerEntry"
            :stats="stats"
            :period="period"
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
              :period="period"
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
                :id="entry.is_current_user ? MY_ROW_ID : undefined"
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
                  'gc-lb-row--trophies': entry.trophies_won > 0,
                }"
              >
                <span class="gc-lb-pos">{{ entry.rank }}</span>
                <div class="gc-lb-av">
                  <MkAvatar
                    :name="entry.display_name || ''"
                    :src="entry.avatar_url || null"
                    :size="24"
                    :tier="entry.tier || 'bronze'"
                  />
                </div>
                <div class="gc-lb-info">
                  <span class="lb-rest-name">
                    <span class="gc-lb-n">{{ entry.display_name }}</span>
                    <LeaderboardMePill v-if="entry.is_current_user" />
                  </span>
                  <span class="gc-lb-tier">
                    <LeaderboardLevelTitle :entry="entry" />
                  </span>
                </div>
                <LeaderboardTrophies class="lb-rest-trophies" :count="entry.trophies_won" />
                <LeaderboardMove :movement="entry.movement" :period="period" />
                <span class="gc-lb-v">{{ (entry.period_xp || 0).toLocaleString() }} XP</span>
              </component>
            </div>
          </div>
        </Transition>
      </template>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, useId, watch } from 'vue'
import { ChevronDown } from 'lucide-vue-next'

import MkAvatar from '@/components/common/MkAvatar.vue'
import LeaderboardHeroBillboard from '@/components/portal/leaderboard/LeaderboardHeroBillboard.vue'
import LeaderboardLevelTitle from '@/components/portal/leaderboard/LeaderboardLevelTitle.vue'
import LeaderboardMePill from '@/components/portal/leaderboard/LeaderboardMePill.vue'
import LeaderboardMove from '@/components/portal/leaderboard/LeaderboardMove.vue'
import LeaderboardPeriodTabs from '@/components/portal/leaderboard/LeaderboardPeriodTabs.vue'
import LeaderboardStatsBar from '@/components/portal/leaderboard/LeaderboardStatsBar.vue'
import PortalLeaderboardPodium from '@/components/portal/leaderboard/PortalLeaderboardPodium.vue'
import LeaderboardMyRankCard from '@/components/portal/leaderboard/LeaderboardMyRankCard.vue'
import LeaderboardTopTenRow from '@/components/portal/leaderboard/LeaderboardTopTenRow.vue'
import LeaderboardTrophies from '@/components/portal/leaderboard/LeaderboardTrophies.vue'
import { useActivityLeaderboard } from '@/composables/portal/useActivityLeaderboard'
import { LEADERBOARD_PAGE_LIMIT, LEADERBOARD_PERIOD } from '@/constants/leaderboard'

const MY_ROW_ID = 'lb-my-row'

const baseId = useId()
const period = ref(LEADERBOARD_PERIOD.MONTH)
const { entries, stats, viewerRank, viewerEntry, loading, fetchTop } = useActivityLeaderboard()

const hero = computed(() => {
  const head = entries.value[0]
  if (!head) return null
  const second = entries.value[1]
  return {
    ...head,
    lead_over_2: second ? (head.period_xp || 0) - (second.period_xp || 0) : 0,
  }
})

const podium = computed(() => entries.value.slice(1, 3))
const topTen = computed(() => entries.value.slice(3, 13))
const rest = computed(() => entries.value.slice(13))

// Below the top ten, a viewer's row is far down the page: the link leads to it.
const myRestEntry = computed(() => rest.value.find(e => e.is_current_user) || null)

function scrollToMyRow() {
  const row = document.getElementById(MY_ROW_ID)
  row.scrollIntoView({ block: 'center' })
  row.focus({ preventScroll: true })
}

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

const loadPeriod = () => fetchTop(LEADERBOARD_PAGE_LIMIT, { period: period.value })

onMounted(loadPeriod)
watch(period, loadPeriod)
</script>

<style>
@import url('@/assets/styles/portal/leaderboard-card.css');
@import url('@/assets/styles/portal/leaderboard-page.css');
</style>
