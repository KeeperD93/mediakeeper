<template>
  <div class="dp">
    <div v-if="loading" class="dp-loading">
      <MkSpinner size="sm" inline />
      {{ $t('common.loading') }}
    </div>

    <template v-else>
      <!-- ═══ DASHBOARD GAMING COMPACT ═══ -->
      <section class="gc dp-reveal" :class="`gc--${rankTier}`">
        <div class="dp-reveal-item dp-reveal-item--d0">
          <RankSidebarCard
            :profile-data="profileData"
            :rank-tier="rankTier"
            :title-key="titleKey"
            :title-tier-name="titleTierName"
            :ranking="ranking"
            :member-since="memberSince"
            :xp-percent="xpPercent"
            :next-level-xp="nextLevelXp"
            :trophies="displayTrophies"
            :icon-map="ICON_MAP"
            @edit-profile="$router.push({ name: 'portal-settings' })"
          />
        </div>

        <!-- ═══ MAIN CONTENT ═══ -->
        <div class="gc-main">
          <div class="dp-reveal-item dp-reveal-item--d1">
            <KpiRow
              :stats="stats"
              :fun-time-comparison="funTimeComparison"
              :format-time="formatTime"
            />
          </div>

          <div class="gc-bottom">
            <div class="dp-reveal-item dp-reveal-item--d2">
              <StatsGenreCard
                :stats="stats"
                :week-data="weekData"
                :top-day="topDay"
                :genre-name="genreName"
                :genre-color="GENRE_COLOR"
                :genre-emoji="GENRE_EMOJI"
                :genre-icon="GENRE_ICON"
              />
            </div>

            <div class="dp-reveal-item dp-reveal-item--d3">
              <TrophyGrid
                :display-trophies="displayTrophies"
                :unlocked-count="displayTrophiesUnlocked"
                :next-achievement="trophies.next_achievement"
                :icon-map="ICON_MAP"
                @select-trophy="openTrophyInOverlay"
                @show-all="showAllTrophies = true"
              />
            </div>

            <div class="dp-reveal-item dp-reveal-item--d4">
              <LeaderboardCard :entries="leaderboardDisplay" />
            </div>
          </div>
        </div>
      </section>

      <ContinueWatchingRow :items="continueWatching" />

      <!-- ═══ 1. MY REQUESTS ═══ -->
      <section v-if="myRequests.length" class="dp-section">
        <MediaCarousel
          :title="$t('portal.profile.myRequests')"
          :items="myRequests"
          card-width="185px"
          :title-route="{ name: 'portal-category', params: { type: 'my-requests' } }"
          @select="showDetail"
          @request="requestItem = $event"
        />
      </section>

      <!-- ═══ 2. LAST 20 PLAYS ═══ -->
      <section v-if="recentWatches.length" class="dp-section">
        <MediaCarousel
          :title="$t('portal.profile.recentWatches')"
          :items="recentWatches"
          card-width="185px"
          :title-route="{ name: 'portal-category', params: { type: 'watch-history' } }"
          @select="showDetail"
        />
      </section>

      <!-- ═══ 3. RECOMMENDATIONS FOR YOU ═══ (clickable → full list) -->
      <section v-if="recommended.length" class="dp-section">
        <MediaCarousel
          :title="$t('portal.sections.recommended')"
          :items="recommended.slice(0, 20)"
          card-width="185px"
          :title-route="{ name: 'portal-category', params: { type: 'recommended-full' } }"
          @select="showDetail"
          @request="requestItem = $event"
        />
      </section>

      <!-- ═══ 4. BECAUSE YOU WATCHED X (SERIES) ═══ -->
      <section
        v-if="becauseYouWatchedTv.items?.length && becauseYouWatchedTv.pivot"
        class="dp-section"
      >
        <MediaCarousel
          :title="
            $t('portal.sections.becauseYouWatched', {
              title: becauseYouWatchedTv.pivot.title || '',
            })
          "
          :items="becauseYouWatchedTv.items.slice(0, 20)"
          card-width="185px"
          @select="showDetail"
          @request="requestItem = $event"
        />
      </section>

      <!-- ═══ 5. BECAUSE YOU WATCHED X (MOVIE) ═══ -->
      <section
        v-if="becauseYouWatchedMovie.items?.length && becauseYouWatchedMovie.pivot"
        class="dp-section"
      >
        <MediaCarousel
          :title="
            $t('portal.sections.becauseYouWatched', {
              title: becauseYouWatchedMovie.pivot.title || '',
            })
          "
          :items="becauseYouWatchedMovie.items.slice(0, 20)"
          card-width="185px"
          @select="showDetail"
          @request="requestItem = $event"
        />
      </section>

      <!-- ═══ 6. BASED ON YOUR PREFERENCES ═══ (clickable → full list) -->
      <section v-if="preferencesBased.length" class="dp-section">
        <MediaCarousel
          :title="$t('portal.sections.preferencesBased')"
          :items="preferencesBased.slice(0, 20)"
          card-width="185px"
          :title-route="{ name: 'portal-category', params: { type: 'preferences-based' } }"
          @select="showDetail"
          @request="requestItem = $event"
        />
      </section>

      <!-- ═══ 7. UNFINISHED SERIES ═══
           Series started but not 100% watched, sorted by fewest
           remaining episodes so the user sees what's closest to done. -->
      <section v-if="nextToFinish.length" class="dp-section">
        <MediaCarousel
          :title="$t('portal.profile.unfinishedSeries')"
          :items="nextToFinish"
          card-width="185px"
          @select="showDetail"
        />
      </section>
    </template>

    <RequestModal
      v-if="requestItem"
      :item="requestItem"
      :is-admin="false"
      @close="requestItem = null"
      @done="onRequestDone"
    />

    <TrophyOverlay
      v-model="showAllTrophies"
      :categories-with-stats="categoriesWithStats"
      :filtered-trophies="filteredTrophies"
      :selected-category="selectedCategory"
      :unlocked-count="displayTrophiesUnlocked"
      :total-count="displayTrophies.length"
      :global-progress-pct="globalProgressPct"
      :icon-map="ICON_MAP"
      :focus-trophy-id="focusTrophyId"
      :pinned-ids="profileData?.selected_badges || []"
      @update:selected-category="selectedCategory = $event"
      @toggle-pin="togglePin"
    />

    <TrophyUnlockToast :unlock="unlockToast" :icon-map="ICON_MAP" @dismiss="unlockToast = null" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import { usePortalAuth } from '@/composables/portal/usePortalAuth'
import { useGenreData } from '@/composables/portal/useGenreData'
import { useProfileXp } from '@/composables/portal/useProfileXp'
import { useTrophyDisplay } from '@/composables/portal/useTrophyDisplay'
import { useProfileData } from '@/composables/portal/useProfileData'
import { useRequestStatus } from '@/composables/portal/useRequestStatus'
import { ICON_MAP } from '@/utils/portal/iconMap'
import MediaCarousel from '@/components/portal/MediaCarousel.vue'
import RequestModal from '@/components/portal/RequestModal.vue'
import RankSidebarCard from '@/components/portal/profile/RankSidebarCard.vue'
import KpiRow from '@/components/portal/profile/KpiRow.vue'
import StatsGenreCard from '@/components/portal/profile/StatsGenreCard.vue'
import LeaderboardCard from '@/components/portal/profile/LeaderboardCard.vue'
import TrophyGrid from '@/components/portal/profile/TrophyGrid.vue'
import TrophyOverlay from '@/components/portal/profile/TrophyOverlay.vue'
import TrophyUnlockToast from '@/components/portal/profile/TrophyUnlockToast.vue'
import ContinueWatchingRow from '@/components/portal/profile/ContinueWatchingRow.vue'
import MkSpinner from '@/components/common/MkSpinner.vue'

import '@/assets/styles/portal/profile-page.css'

const router = useRouter()
const { profile: profileData } = usePortalAuth()

const {
  loading,
  stats,
  recoItems,
  genreIds,
  recentWatches,
  myRequests,
  nextToFinish,
  continueWatching,
  ranking,
  titleKey,
  rankTier,
  trophies,
  recentUnlock,
  markTrophyShown,
  recommended,
  becauseYouWatchedTv,
  becauseYouWatchedMovie,
  preferencesBased,
  load,
} = useProfileData()

const requestItem = ref(null)
const { markRequested } = useRequestStatus()

// RequestModal's ``done`` event fires after a successful resubmission
// (or first submission). We stamp the global request-status cache so the
// MediaCard on this page flips from "Re-request" to the greyed-out
// "Requested" state without needing a reload.
function onRequestDone(payload) {
  const id = requestItem.value?.tmdb_id || requestItem.value?.id
  if (id) {
    markRequested(id, {
      retry_count: payload?.retry_count || 0,
      request_id: payload?.id || null,
    })
  }
  requestItem.value = null
}

// Genre helpers still drive the stats card (genre icons / colors) even
// now that the "Because you like {genre}" strip has been retired
// in favour of the user-driven "Based on your preferences" carousel.
const { genreName, GENRE_COLOR, GENRE_EMOJI, GENRE_ICON } = useGenreData(recoItems, genreIds)
const {
  titleTierName,
  memberSince,
  xpPercent,
  nextLevelXp,
  weekData,
  topDay,
  funTimeComparison,
  formatTime,
} = useProfileXp(profileData, stats)
const {
  showAllTrophies,
  selectedCategory,
  unlockToast,
  displayTrophies,
  displayTrophiesUnlocked,
  categoriesWithStats,
  filteredTrophies,
  globalProgressPct,
  togglePin,
} = useTrophyDisplay(trophies, profileData)

// Forward the most recently unlocked trophy (if any) into the toast
// state owned by useTrophyDisplay. Auto-hide 5s later, matching the
// previous inline behaviour.
watch(recentUnlock, unlocked => {
  if (!unlocked) return
  unlockToast.value = unlocked
  // Mark the trophy as already-celebrated so refreshing the profile
  // within the 5-min unlock window doesn't pop the toast a second time.
  markTrophyShown(unlocked.id)
  setTimeout(() => {
    unlockToast.value = null
  }, 5000)
})

const leaderboardDisplay = computed(() => ranking.value.leaderboard || [])

const focusTrophyId = ref(null)
async function openTrophyInOverlay(trophy) {
  if (!trophy) return
  if (trophy.category) selectedCategory.value = trophy.category
  focusTrophyId.value = null
  await nextTick()
  focusTrophyId.value = trophy.id
  showAllTrophies.value = true
}

function showDetail(item) {
  const type = item.media_type || 'movie'
  const id = item.tmdb_id || item.id
  router.push({ name: 'portal-media-detail', params: { type, id } })
}

onMounted(load)
</script>
