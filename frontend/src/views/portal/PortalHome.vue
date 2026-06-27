<template>
  <div class="pt-home">
    <HeroBanner
      v-if="heroItems.length"
      :item="heroItems[heroIndex]"
      :next-item="heroItems[(heroIndex + 1) % heroItems.length]"
      :current-index="heroIndex"
      :total-items="heroItems.length"
      :rank="heroIndex >= featuredCount ? heroIndex - featuredCount + 1 : 0"
      :is-featured="heroIndex < featuredCount"
      @request="handleRequest(heroItems[heroIndex])"
      @detail="showDetail(heroItems[heroIndex])"
      @goto="gotoHero"
      @trailer-open="heroPaused = true"
      @trailer-close="heroPaused = false"
    />

    <div class="pt-home-body">
      <!-- Initial skeleton: shown only while NO carousel has any data
           yet. Each row below appears independently as its endpoint
           responds, so we no longer wait for the slowest request
           before showing anything. -->
      <div v-if="showInitialSkeleton" class="pt-skeleton-row">
        <SkeletonCard v-for="i in 7" :key="i" width="185px" />
      </div>

      <!-- 1. Top 20 du mois sur Emby — NON cliquable -->
      <Top20Carousel
        v-if="top20.length"
        :title="$t('portal.sections.top20')"
        :items="top20.slice(0, 20)"
        @select="showDetail"
      />

      <!-- 2. Recommandations for vous -->
      <MediaCarousel
        v-if="recommended.length"
        :title="$t('portal.sections.recommended')"
        :items="recommended.slice(0, 20)"
        card-width="185px"
        :title-route="{ name: 'portal-category', params: { type: 'recommended-full' } }"
        @select="showDetail"
        @request="handleRequest"
      />

      <!-- 3. Films populaires -->
      <MediaCarousel
        v-if="popularMovies.length"
        :title="$t('portal.sections.popularMovies')"
        :items="popularMovies.slice(0, 20)"
        card-width="185px"
        :title-route="{ name: 'portal-category', params: { type: 'popular-movies' } }"
        @select="showDetail"
        @request="handleRequest"
      />

      <!-- 4. Seriess populaires -->
      <MediaCarousel
        v-if="popularTv.length"
        :title="$t('portal.sections.popularTv')"
        :items="popularTv.slice(0, 20)"
        card-width="185px"
        :title-route="{ name: 'portal-category', params: { type: 'popular-tv' } }"
        @select="showDetail"
        @request="handleRequest"
      />

      <!-- 5. Because you watched X — NOT clickable (personal pivot) -->
      <MediaCarousel
        v-if="becauseYouWatched.items?.length && becauseYouWatched.pivot"
        :title="becauseYouWatchedTitle"
        :items="becauseYouWatched.items.slice(0, 20)"
        card-width="185px"
        @select="showDetail"
        @request="handleRequest"
      />

      <!-- 6. Categorys par genres — header non cliquable, cartes cliquables -->
      <CategoryCards :title="$t('portal.sections.genres')" :items="genres" @select="goGenre" />

      <!-- 7. Recently added to Emby — scroll-triggered hero.
             @select is intentionally NOT bound here. Clicking a poster
             inside the mini hero must update the hero strip (handled
             internally by EmbyRecentHero), not navigate. The
             "Plus d'infos" button on the right of the hero emits
             @detail which is the only thing routed to the detail page.
             The 21st card is an Emby-branded "See more" shortcut to
             the full paginated recently-added list. -->
      <EmbyRecentHero
        v-if="recentEmby.length"
        :items="recentEmby"
        @detail="showDetail"
        @request="handleRequest"
        @add-watchlist="addToWatchlist"
      />

      <!-- 8. Prochainement -->
      <MediaCarousel
        v-if="upcoming.length"
        :title="$t('portal.sections.upcoming')"
        :items="upcoming.slice(0, 20)"
        card-width="185px"
        :title-route="{ name: 'portal-category', params: { type: 'upcoming' } }"
        @select="showDetail"
        @request="handleRequest"
      />

      <!-- 9. Top rated this year -->
      <MediaCarousel
        v-if="topRatedYear.length"
        :title="topRatedYearTitle"
        :items="topRatedYear.slice(0, 20)"
        card-width="185px"
        :title-route="{ name: 'portal-category', params: { type: 'top-rated-year' } }"
        @select="showDetail"
        @request="handleRequest"
      />

      <!-- 10. Platforms (international + FR merged) -->
      <CategoryCards
        :title="$t('portal.sections.platforms')"
        :items="allPlatforms"
        @select="goPlatform"
      />

      <!-- 11. Oscars & award winners -->
      <MediaCarousel
        v-if="oscars.length"
        :title="$t('portal.sections.oscars')"
        :items="oscars.slice(0, 20)"
        card-width="185px"
        :title-route="{ name: 'portal-category', params: { type: 'oscars' } }"
        @select="showDetail"
        @request="handleRequest"
      />

      <!-- 12. Family-friendly -->
      <MediaCarousel
        v-if="family.length"
        :title="$t('portal.sections.family')"
        :items="family.slice(0, 20)"
        card-width="185px"
        :title-route="{ name: 'portal-category', params: { type: 'family' } }"
        @select="showDetail"
        @request="handleRequest"
      />

      <!-- 13. Animation — series only -->
      <MediaCarousel
        v-if="animation.length"
        :title="$t('portal.sections.animation')"
        :items="animation.slice(0, 20)"
        card-width="185px"
        :title-route="{ name: 'portal-category', params: { type: 'animation' } }"
        @select="showDetail"
        @request="handleRequest"
      />
    </div>

    <RequestModal
      v-if="requestItem"
      :item="requestItem"
      :is-admin="isAdmin"
      @close="requestItem = null"
      @done="onRequestDone"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onActivated } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useApi } from '@/composables/useApi'
import { usePortalAuth } from '@/composables/portal/usePortalAuth'
import { usePortalHomeData } from '@/composables/portal/usePortalHomeData'
import { useRequestStatus } from '@/composables/portal/useRequestStatus'
import { usePortalRequestFeedback } from '@/composables/portal/usePortalRequestFeedback'
import HeroBanner from '@/components/portal/HeroBanner.vue'
import Top20Carousel from '@/components/portal/Top20Carousel.vue'
import MediaCarousel from '@/components/portal/MediaCarousel.vue'
import EmbyRecentHero from '@/components/portal/EmbyRecentHero.vue'
import CategoryCards from '@/components/portal/CategoryCards.vue'
import SkeletonCard from '@/components/portal/SkeletonCard.vue'
import RequestModal from '@/components/portal/RequestModal.vue'
import { buildGenres, buildPlatforms, PROVIDER_ID_TO_SLUG } from '@/constants/portal-home'
import { MEDIA_TYPE, isTv } from '@/constants/media'
import { USER_ROLE } from '@/constants/auth'

import '@/assets/styles/portal/home.css'

const router = useRouter()
const { t } = useI18n()
const { apiPost } = useApi()
const { profile } = usePortalAuth()

const { markRequested } = useRequestStatus()
const { presentRequestResult } = usePortalRequestFeedback()
const isAdmin = computed(() => profile.value?.role === USER_ROLE.ADMIN)
const requestItem = ref(null)

const {
  top20,
  popularMovies,
  popularTv,
  recentEmby,
  upcoming,
  topRatedYear,
  recommended,
  oscars,
  family,
  animation,
  becauseYouWatched,
  loadingAll,
  heroItems,
  heroIndex,
  heroPaused,
  featuredCount,
  gotoHero,
  loadAllData,
} = usePortalHomeData()

// Hide the initial skeleton as soon as ANY row has landed — the hero
// banner and the first carousel become the loading anchors. Without
// this, the skeleton would sit above real carousels until the slowest
// endpoint (typically recommended-for-me / because-you-watched) came
// back, which is exactly what the all-or-nothing gate used to do.
const showInitialSkeleton = computed(
  () =>
    loadingAll.value &&
    !heroItems.value.length &&
    !top20.value.length &&
    !popularMovies.value.length &&
    !popularTv.value.length &&
    !recentEmby.value.length,
)

const currentYear = new Date().getFullYear()
const topRatedYearTitle = computed(() => t('portal.sections.topRatedYear', { year: currentYear }))
const becauseYouWatchedTitle = computed(() =>
  t('portal.sections.becauseYouWatched', { title: becauseYouWatched.value.pivot?.title || '' }),
)

const genres = computed(() => buildGenres(t))
const allPlatforms = computed(() => buildPlatforms())

function showDetail(item) {
  const type = item.media_type || MEDIA_TYPE.MOVIE
  const id = item.tmdb_id || item.id
  router.push({ name: 'portal-media-detail', params: { type, id } })
}

// Genre card click → paginated discover page. The backend recognises
// slugs prefixed with "genre-" and applies the per-media-type genre
// filters registered in CATEGORY_FILTERS.
function goGenre(g) {
  router.push({ name: 'portal-category', params: { type: `genre-${g.key}` } })
}

function goPlatform(plat) {
  const slug = PROVIDER_ID_TO_SLUG[plat.providerId] || plat.key || 'netflix'
  router.push({ name: 'portal-provider', params: { slug } })
}

async function addToWatchlist(item) {
  // Lightweight watchlist add — defers to the lists view if the user
  // wants to organise further. We never block the UX waiting for this.
  if (!item) return
  await apiPost('/api/portal/social/lists/default/items', {
    tmdb_id: item.tmdb_id || item.id,
    media_type: item.media_type || MEDIA_TYPE.MOVIE,
    title: item.title,
  }).catch(() => null)
}

function onRequestDone(payload) {
  if (requestItem.value) {
    markRequested(requestItem.value.tmdb_id || requestItem.value.id, {
      retry_count: payload?.retry_count || 0,
      request_id: payload?.id || null,
    })
  }
  requestItem.value = null
}

async function handleRequest(item) {
  if (isAdmin.value) {
    requestItem.value = item
    return
  }
  if (isTv(item)) {
    requestItem.value = item
    return
  }
  let res = null
  let errorCode = null
  try {
    res = await apiPost('/api/portal/requests', {
      tmdb_id: item.tmdb_id || item.id,
      media_type: MEDIA_TYPE.MOVIE,
      title: item.title,
      year: item.year ? parseInt(item.year) : null,
      poster_url: item.poster_url || item.poster || '',
    })
  } catch (e) {
    errorCode = e?.message || null
  }
  if (res?.success) {
    markRequested(item.tmdb_id || item.id)
  }
  presentRequestResult(res, errorCode)
}

onMounted(loadAllData)
onActivated(loadAllData)
</script>
