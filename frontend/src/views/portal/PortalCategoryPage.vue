<template>
  <PortalDiscoverPage :key="$route.params.type" :title="title" :endpoint="endpoint" />
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import PortalDiscoverPage from './PortalDiscoverPage.vue'

// Map URL slug -> i18n title key. Every slug used by a `title-route`
// on the Portal home MUST have an entry here, otherwise the browse
// page falls back to "Films" as title which is confusing.
const CATEGORY_TITLES = {
  // Base catalogues
  movies: 'portal.categories.movies',
  series: 'portal.categories.series',
  documentaries: 'portal.categories.documentaries',
  anime: 'portal.categories.anime',
  shows: 'portal.categories.shows',
  // Home row → browse page mappings
  'popular-movies': 'portal.sections.popularMovies',
  'popular-tv': 'portal.sections.popularTv',
  upcoming: 'portal.sections.upcoming',
  'top-rated-year': 'portal.sections.topRatedYear',
  oscars: 'portal.sections.oscars',
  family: 'portal.sections.family',
  animation: 'portal.sections.animation',
  // Emby-backed
  'recently-added': 'portal.sections.recentlyAdded',
  // 12 genres
  'genre-action': 'portal.genres.action',
  'genre-comedie': 'portal.genres.comedie',
  'genre-drame': 'portal.genres.drame',
  'genre-thriller': 'portal.genres.thriller',
  'genre-aventure': 'portal.genres.aventure',
  'genre-horreur': 'portal.genres.horreur',
  'genre-science-fiction': 'portal.genres.scienceFiction',
  'genre-animation': 'portal.genres.animation',
  'genre-fantastique': 'portal.genres.fantastique',
  'genre-familial': 'portal.genres.familial',
  'genre-documentaire': 'portal.genres.documentaire',
  'genre-mystere': 'portal.genres.mystere',
  // Profile sub-pages (full history / full requests)
  'watch-history': 'portal.profile.recentWatches',
  'my-requests': 'portal.profile.myRequests',
  'recommended-full': 'portal.sections.recommended',
  'preferences-based': 'portal.sections.preferencesBased',
}

const route = useRoute()
const { t } = useI18n()

const slug = computed(() => route.params.type || 'movies')

const title = computed(() => {
  const key = CATEGORY_TITLES[slug.value]
  if (!key) return slug.value
  // top-rated-year needs the current year interpolated
  if (slug.value === 'top-rated-year') {
    return t(key, { year: new Date().getFullYear() })
  }
  return t(key)
})

// Profile sub-pages use dedicated paginated endpoints (they return
// user-scoped data, not a TMDB category). Everything else goes through
// the generic /category/{slug} route.
const SPECIAL_ENDPOINTS = {
  'watch-history': '/api/portal/catalog/watch-history',
  'my-requests': '/api/portal/catalog/my-requests',
  'recommended-full': '/api/portal/catalog/recommended-full',
  'preferences-based': '/api/portal/catalog/preferences-based',
}

const endpoint = computed(
  () => SPECIAL_ENDPOINTS[slug.value] || `/api/portal/catalog/category/${slug.value}`,
)
</script>
