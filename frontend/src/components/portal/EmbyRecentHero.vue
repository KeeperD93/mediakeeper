<template>
  <section class="pt-eh">
    <TrailerLightbox v-if="lightboxOpen && trailer" :trailer="trailer" @close="closeLightbox" />

    <div class="pt-eh-hero" @click="onHeroTap">
      <div
        class="pt-eh-hero-bg"
        :class="{ 'pt-eh-hero-bg--hidden': (trailer && videoPlaying) || transitioning }"
        :style="bgStyle"
      />

      <div
        v-if="trailer"
        class="pt-eh-hero-video"
        :class="{ 'pt-eh-hero-video--playing': videoPlaying }"
      >
        <video
          v-if="trailer.source === TRAILER_SOURCE.EMBY"
          ref="embyVideoRef"
          :src="trailer.url"
          autoplay
          :muted="muted"
          playsinline
          class="pt-eh-emby-video"
          @playing="setVideoPlaying(true)"
          @pause="onEmbyPause"
          @ended="onEmbyEnded"
        />
        <template v-else>
          <div class="pt-eh-player-wrap">
            <div :id="playerId" />
          </div>
          <div class="pt-eh-video-block" />
        </template>
      </div>

      <div class="pt-eh-gradient-top" />
      <div class="pt-eh-gradient-bottom" />

      <div class="pt-eh-fade" :class="{ 'pt-eh-fade--active': transitioning }" :style="fadeStyle" />

      <div class="pt-eh-content">
        <h3 class="pt-eh-row-title">{{ $t('portal.sections.recentlyAdded') }}</h3>
        <h2 class="pt-eh-item-title">{{ currentItem?.title }}</h2>
        <div class="pt-eh-meta">
          <span v-if="currentItem?.vote" class="pt-eh-vote">★ {{ currentItem.vote }}</span>
          <span v-if="currentItem?.year">{{ currentItem.year }}</span>
        </div>
        <p v-if="currentItem?.overview" class="pt-eh-overview">{{ currentItem.overview }}</p>
        <div class="pt-eh-actions">
          <a
            v-if="currentItem?.emby_url"
            :href="currentItem.emby_url"
            target="_blank"
            class="pt-eh-btn pt-eh-btn--play"
          >
            <img src="/assets/icons/emby.svg" alt="" class="pt-eh-btn-emby" />
            {{ $t('portal.hero.play') }}
          </a>
          <button v-if="trailer" class="pt-eh-btn pt-eh-btn--trailer" @click="openLightbox">
            <Video :size="20" />
            {{ $t('portal.detail.watchTrailer') }}
          </button>
          <button
            class="pt-eh-btn pt-eh-btn--info pt-eh-btn--icon"
            :aria-label="$t('portal.moreInfo')"
            @click="emit('detail', currentItem)"
          >
            <Info :size="22" :stroke-width="2" />
          </button>
        </div>
      </div>

      <button v-if="trailer" class="pt-eh-mute" @click="onMuteToggle">
        <VolumeX v-if="muted" :size="18" />
        <Volume2 v-else :size="18" />
      </button>
    </div>

    <div class="pt-eh-row">
      <div ref="trackRef" class="pt-eh-track" @scroll="updateArrows">
        <div class="pt-eh-track-padding" />
        <MediaCard
          v-for="(item, idx) in visibleItems"
          :key="item.id || item.tmdb_id || idx"
          :item="item"
          :class="{ 'pt-eh-card--active': idx === currentIndex }"
          width="185px"
          @select="onPosterClick(item, idx)"
          @request="$emit('request', item)"
        />
        <button
          v-if="showSeeMoreCard"
          class="pt-eh-seemore"
          @click="$router.push({ name: 'portal-category', params: { type: 'recently-added' } })"
        >
          <img src="/assets/icons/emby.svg" alt="" class="pt-eh-seemore-logo" />
          <span class="pt-eh-seemore-label">{{ $t('portal.seeMore') }}</span>
        </button>
        <div class="pt-eh-track-padding" />
      </div>

      <div
        class="pt-edge-fade pt-edge-fade--left"
        :class="{ 'pt-edge-fade--visible': canScrollLeft }"
      />
      <div
        class="pt-edge-fade pt-edge-fade--right"
        :class="{ 'pt-edge-fade--visible': canScrollRight }"
      />

      <button
        class="pt-carousel-arrow pt-carousel-arrow--left"
        :class="{ 'pt-carousel-arrow--visible': canScrollLeft }"
        :aria-label="$t('common.previous')"
        @click="scrollTrack(-1)"
      >
        <ChevronLeft :size="26" :stroke-width="2.8" />
      </button>
      <button
        class="pt-carousel-arrow pt-carousel-arrow--right"
        :class="{ 'pt-carousel-arrow--visible': canScrollRight }"
        :aria-label="$t('common.next')"
        @click="scrollTrack(1)"
      >
        <ChevronRight :size="26" :stroke-width="2.8" />
      </button>
    </div>
  </section>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import MediaCard from './MediaCard.vue'
import TrailerLightbox from './TrailerLightbox.vue'
import { useEmbyHeroTrailer } from '@/composables/portal/useEmbyHeroTrailer'
import { useHeroCinemaVeil } from '@/composables/portal/useHeroCinemaVeil'
import { ChevronLeft, ChevronRight, Info, Video, Volume2, VolumeX } from 'lucide-vue-next'
import { TRAILER_SOURCE } from '@/constants/trailers'

import '@/assets/styles/portal/emby-recent-hero-hero.css'
import '@/assets/styles/portal/emby-recent-hero-row.css'

const props = defineProps({
  items: { type: Array, default: () => [] },
})
const emit = defineEmits(['request', 'detail', 'add-watchlist', 'select'])

const ROTATE_MS = 25000
const MAX_VISIBLE = 20

const currentIndex = ref(0)
const lightboxOpen = ref(false)
const canScrollLeft = ref(false)
const canScrollRight = ref(false)
const trackRef = ref(null)

const visibleItems = computed(() => props.items.slice(0, MAX_VISIBLE))
const showSeeMoreCard = computed(() => props.items.length > 0)
const heroPool = computed(() => visibleItems.value)
const currentItem = computed(() => heroPool.value[currentIndex.value] || null)

const bgStyle = computed(() => {
  const bg = currentItem.value?.backdrop || currentItem.value?.poster_url || ''
  return bg ? { backgroundImage: `url(${bg})` } : {}
})

let rotateTimer = null
function nextItem() {
  if (!heroPool.value.length) return
  currentIndex.value = (currentIndex.value + 1) % heroPool.value.length
}
function startTimer() {
  stopTimer()
  rotateTimer = setInterval(() => {
    if (heroPool.value.length > 1 && !lightboxOpen.value) nextItem()
  }, ROTATE_MS)
}
function stopTimer() {
  if (rotateTimer) {
    clearInterval(rotateTimer)
    rotateTimer = null
  }
}

const {
  trailer,
  muted,
  embyVideoRef,
  videoPlaying,
  playerId,
  loadTrailer,
  peekTrailer,
  setVideoPlaying,
  toggleMute,
  onEmbyPause,
  onEmbyEnded,
} = useEmbyHeroTrailer({ onTrailerEnded: nextItem })

function peekItemTrailer(item) {
  if (!item) return undefined
  return peekTrailer(item.media_type || 'movie', item.tmdb_id || item.id, item.emby_item_id || null)
}
const {
  transitioning,
  fadeStyle,
  onItemChange,
  startInitial,
  dispose: disposeVeil,
} = useHeroCinemaVeil({
  videoPlaying,
  peekItem: peekItemTrailer,
  loadItem: it => loadTrailer(it),
  hasTrailer: () => !!trailer.value,
})

function onMuteToggle() {
  toggleMute()
  if (muted.value) startTimer()
  else stopTimer()
}

function onHeroTap(e) {
  if (!trailer.value) return
  if (window.innerWidth >= 640) return
  if (e.target.closest('button, a, input, select, textarea')) return
  onMuteToggle()
}

function openLightbox() {
  lightboxOpen.value = true
  stopTimer()
}
function closeLightbox() {
  lightboxOpen.value = false
  startTimer()
}

function onPosterClick(item, idx) {
  currentIndex.value = idx
}

function updateArrows() {
  const el = trackRef.value
  if (!el) return
  canScrollLeft.value = el.scrollLeft > 32
  canScrollRight.value = el.scrollLeft + el.clientWidth < el.scrollWidth - 32
}

function scrollTrack(dir) {
  const el = trackRef.value
  if (!el) return
  const firstCard = el.querySelector('.pt-card, .pt-eh-seemore')
  if (!firstCard) return
  const cardRect = firstCard.getBoundingClientRect()
  const trackRect = el.getBoundingClientRect()

  let gap = 12
  const cards = el.querySelectorAll('.pt-card, .pt-eh-seemore')
  if (cards.length >= 2) {
    const a = cards[0].getBoundingClientRect()
    const b = cards[1].getBoundingClientRect()
    gap = b.left - a.right
  }
  const step = cardRect.width + gap
  if (step <= 0) return

  const visible = Math.max(1, Math.floor(trackRect.width / step))
  el.scrollBy({ left: dir * visible * step, behavior: 'smooth' })
}

watch(currentItem, it => onItemChange(it))
watch(
  () => props.items.length,
  () => {
    if (props.items.length && !trailer.value) startInitial(currentItem.value)
    nextTick(updateArrows)
  },
)

let resizeObs = null
onMounted(() => {
  startInitial(currentItem.value)
  startTimer()
  if (trackRef.value) {
    resizeObs = new ResizeObserver(updateArrows)
    resizeObs.observe(trackRef.value)
    nextTick(updateArrows)
  }
})

onBeforeUnmount(() => {
  stopTimer()
  resizeObs?.disconnect()
  disposeVeil()
})
</script>
