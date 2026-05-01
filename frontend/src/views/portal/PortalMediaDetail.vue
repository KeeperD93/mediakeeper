<template>
  <div class="vmd2-root">
    <template v-if="media">
      <DetailHero
        :media="media"
        :avail-info="availInfo"
        :req-status="reqStatus"
        :show-request-btn="showRequestBtn"
        :trailer-key="trailerKey"
        @request="onRequestClick"
        @open-trailer="openTrailer"
        @add-to-list="addToList"
      />

      <div class="vmd2-tabs-wrap">
        <TabStrip v-model="activeTab" :tabs="tabStripItems" placement="top" />
      </div>

      <DetailOverview v-show="activeTab === 'overview'" :media="media" />
      <DetailCastCrew v-show="activeTab === 'cast'" :media="media" />
      <DetailExtras v-show="activeTab === 'extras'" :media="media" />

      <section v-show="activeTab === 'similar'" class="vmd2-similar-wrap">
        <MediaCarousel
          v-if="media.recommendations?.length"
          :title="$t('portal.detail.recommendations')"
          :items="media.recommendations"
          card-width="160px"
          @select="goToDetail"
          @request="handleCarouselRequest"
        />
        <DetailCarousels
          :director="media.directors?.[0]"
          :lead-actor="leadActor"
          :director-filmo="directorFilmo"
          :actor-filmo="actorFilmo"
          :collection="null"
          @select="goToDetail"
          @request="handleCarouselRequest"
        />
      </section>

      <div
        v-if="collection?.collection"
        class="vmd2-collection"
      >
        <div
          class="vmd2-collection-bg"
          :style="collection.collection.backdrop
            ? { backgroundImage: `url(${collection.collection.backdrop})` }
            : null"
        />
        <div class="vmd2-collection-body">
          <div class="vmd2-collection-kicker">{{ $t('portal.detail.sagaLabel') }}</div>
          <h2 class="vmd2-collection-title">{{ collection.collection.name }}</h2>
          <p
            v-if="collection.collection.overview"
            class="vmd2-overview vmd2-collection-overview"
          >{{ collection.collection.overview }}</p>
          <div class="vmd2-scroller">
            <MediaCard
              v-for="m in collection.items" :key="m.tmdb_id || m.id"
              :item="m"
              width="160px"
              @select="goToDetail"
              @request="handleCarouselRequest"
            />
          </div>
        </div>
      </div>
    </template>

    <div v-else class="vmd2-loading">
      <MkSpinner size="lg" />
    </div>

    <RequestModal
      v-if="requestItem"
      :item="requestItem"
      :is-admin="isAdmin"
      @close="requestItem = null"
      @done="onRequestDone"
    />

    <TrailerLightbox
      v-if="trailerOpen && activeTrailer"
      :trailer="activeTrailer"
      @close="trailerOpen = false"
    />

    <AddToListOverlay
      :open="addToListOpen"
      :media="media"
      @close="addToListOpen = false"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useApi } from '@/composables/useApi'
import { useTrailer } from '@/composables/portal/useTrailer'
import { useAvailability } from '@/composables/portal/useAvailability'
import { useRequestStatus } from '@/composables/portal/useRequestStatus'
import { usePortalAuth } from '@/composables/portal/usePortalAuth'
import { useDetailExtras } from '@/composables/portal/useDetailExtras'

import MediaCarousel from '@/components/portal/MediaCarousel.vue'
import MediaCard from '@/components/portal/MediaCard.vue'
import RequestModal from '@/components/portal/RequestModal.vue'
import AddToListOverlay from '@/components/portal/lists/AddToListOverlay.vue'
import TrailerLightbox from '@/components/portal/TrailerLightbox.vue'
import DetailCarousels from '@/components/portal/detail/DetailCarousels.vue'
import DetailHero from '@/components/portal/detail/DetailHero.vue'
import MkSpinner from '@/components/common/MkSpinner.vue'
import DetailOverview from '@/components/portal/detail/DetailOverview.vue'
import DetailCastCrew from '@/components/portal/detail/DetailCastCrew.vue'
import DetailExtras from '@/components/portal/detail/DetailExtras.vue'
import TabStrip from '@/components/common/TabStrip.vue'
import { useI18n } from 'vue-i18n'
import { MEDIA_TYPE, isTv } from '@/constants/media'
import { REQUEST_STATUS } from '@/constants/requests'
import { TRAILER_SOURCE } from '@/constants/trailers'
import { USER_ROLE } from '@/constants/auth'

import '@/assets/styles/portal/media-detail-premium.css'

const { t } = useI18n()

const route = useRoute()
const router = useRouter()
const { apiGet, apiPost } = useApi()
const { trailer, resolve: resolveTrailer, clear: clearTrailer } = useTrailer()
const { checkAvailability, getAvailability } = useAvailability()
const { checkStatus: checkRequestStatus, getStatus, markRequested } = useRequestStatus()
const { profile } = usePortalAuth()
const { directorFilmo, actorFilmo, collection, load: loadExtras, reset: resetExtras } = useDetailExtras()

const media = ref(null)
const trailerOpen = ref(false)
const requestItem = ref(null)
const addToListOpen = ref(false)
const activeTab = ref('overview')

const tabStripItems = computed(() => [
  { id: 'overview', label: t('portal.detail.tabs.overview') },
  { id: 'cast',     label: t('portal.detail.tabs.cast') },
  { id: 'extras',   label: t('portal.detail.tabs.extras') },
  { id: 'similar',  label: t('portal.detail.tabs.similar') },
])

const leadActor = computed(() => media.value?.cast?.[0] || null)
const trailerKey = computed(() =>
  trailer.value?.key || media.value?.videos?.[0]?.key || null,
)

// Descriptor consumed by TrailerLightbox. Prefer the Emby-cascade
// resolver's descriptor (includes source=emby when a LocalTrailer was
// found) and fall back to a YouTube URL built from the first media
// video so the lightbox can still play something in Emby-less libs.
const activeTrailer = computed(() => {
  if (trailer.value?.url) return trailer.value
  const key = media.value?.videos?.[0]?.key
  if (!key) return null
  return { source: TRAILER_SOURCE.YOUTUBE, url: `https://www.youtube.com/embed/${key}`, key }
})

function openTrailer() {
  if (activeTrailer.value) trailerOpen.value = true
}
const isAdmin = computed(() => profile.value?.role === USER_ROLE.ADMIN)

const availInfo = computed(() => {
  const id = media.value?.tmdb_id || media.value?.id
  return id ? getAvailability(id) : null
})
const reqStatus = computed(() => {
  const id = media.value?.tmdb_id || media.value?.id
  const status = id ? getStatus(id) : null
  return status?.status || null
})

const showRequestBtn = computed(() => {
  if (!media.value) return false
  if (!availInfo.value?.emby_url) return true
  return availInfo.value?.availability === 'partial'
})

function onRequestClick() {
  if (reqStatus.value && reqStatus.value !== REQUEST_STATUS.REJECTED) return
  if (!media.value) return
  requestItem.value = {
    ...media.value,
    poster_url: media.value.poster || media.value.poster_url || '',
  }
}

// Carousel cards ("See also") trigger the same request flow as the
// home page: open the modal for admins or TV shows (season picker),
// fire-and-forget POST for movies.
async function handleCarouselRequest(item) {
  if (!item) return
  if (isAdmin.value || isTv(item)) {
    requestItem.value = {
      ...item,
      poster_url: item.poster_url || item.poster || '',
    }
    return
  }
  const id = item.tmdb_id || item.id
  const res = await apiPost('/api/portal/requests', {
    tmdb_id: id,
    media_type: MEDIA_TYPE.MOVIE,
    title: item.title,
    year: item.year ? parseInt(item.year) : null,
    poster_url: item.poster_url || item.poster || '',
  }).catch(() => null)
  if (res?.success && id) {
    markRequested(id, { request_id: res.id || null })
  }
}

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

function addToList() {
  addToListOpen.value = true
}

function goToDetail(item) {
  const type = item.media_type || MEDIA_TYPE.MOVIE
  const id = item.tmdb_id || item.id
  router.push({ name: 'portal-media-detail', params: { type, id } })
}

async function loadMedia() {
  media.value = null
  trailerOpen.value = false
  activeTab.value = 'overview'
  resetExtras()
  clearTrailer()

  const { type, id } = route.params
  const res = await apiGet(`/api/portal/catalog/detail/${type}/${id}`).catch(() => null)
  if (!res) return
  media.value = res
  await resolveTrailer(type, id, res.emby_item_id || null)

  const mediaItem = { tmdb_id: res.tmdb_id || res.id, media_type: type }
  await Promise.all([
    checkAvailability([mediaItem]),
    checkRequestStatus([mediaItem]),
    loadExtras(res),
  ])

  // Prime availability + request-status caches for every card displayed
  // under "See also" (recommendations + filmographies + franchise) so
  // their MediaCard instances render the same play button / green-orange
  // dot / tags as on the home page. Must run after loadExtras.
  const extraItems = [
    ...(res.recommendations || []),
    ...directorFilmo.value.items,
    ...actorFilmo.value.items,
    ...(collection.value?.items || []),
  ]
  if (extraItems.length) {
    await Promise.all([
      checkAvailability(extraItems),
      checkRequestStatus(extraItems),
    ])
  }
}

watch(() => route.params.id, loadMedia)

onMounted(loadMedia)
</script>
