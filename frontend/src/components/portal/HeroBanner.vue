<template>
  <div ref="heroRef" class="pt-hero" @click="onHeroTap">
    <!-- Background image — hidden while a trailer is playing AND during
         the cinematic fade-to-black between two trailers, so the new
         item's backdrop never briefly appears behind the black veil. -->
    <div
      class="pt-hero-bg"
      :class="{ 'pt-hero-bg--hidden': (trailer && videoPlaying) || transitioning }"
      :style="bgStyle"
    />

    <!-- Trailer slot — switches between native <video> (Emby local trailer
         streamed via the backend proxy) and the YouTube IFrame API. The
         layer stays transparent until `videoPlaying` is true so the YT
         buffering chrome (loading spinner, Play overlay) never shows;
         the backdrop image underneath covers the gap between two
         trailers. -->
    <div v-if="trailer" class="pt-hero-video" :class="{ 'pt-hero-video--playing': videoPlaying }">
      <video
        v-if="trailer.source === TRAILER_SOURCE.EMBY"
        ref="embyVideoRef"
        :src="trailer.url"
        autoplay
        :muted="muted"
        playsinline
        class="pt-hero-emby-video"
        @playing="setVideoPlaying(true)"
        @pause="onEmbyPause"
        @ended="onEmbyEnded"
      />
      <template v-else>
        <div class="pt-hero-player-wrap">
          <div :id="playerId" />
        </div>
        <div class="pt-hero-video-block" />
      </template>
    </div>

    <div class="pt-hero-vignette" />
    <div class="pt-hero-gradient-bottom" />
    <div class="pt-hero-gradient-left" />

    <!-- Black veil during item changes. Covers the video + backdrop so
         the user sees a clean fade-to-black between two trailers while
         the next one buffers. The transition duration is asymmetric
         (short fade-in at the end of A, longer fade-out onto B). -->
    <div
      class="pt-hero-fade"
      :class="{ 'pt-hero-fade--active': transitioning }"
      :style="fadeStyle"
    />

    <div class="pt-hero-content">
      <div v-if="isTv(item)" class="pt-hero-badge">
        {{ $t('portal.hero.series') }}
      </div>

      <h1 class="pt-hero-title" :class="{ 'pt-hero-title--available': item?.emby_url }">
        <span class="pt-hero-title-text">{{ item.title }}</span>
      </h1>

      <div v-if="isFeatured" class="pt-hero-rank">
        <img src="/assets/icons/emby.svg" alt="Emby" class="pt-hero-rank-emby" />
        {{ $t('portal.hero.featured') }}
      </div>
      <div v-else-if="rank" class="pt-hero-rank">
        <span>🔥</span>
        {{ $t('portal.hero.topRank', { rank }) }}
      </div>

      <p class="pt-hero-overview">{{ item.overview }}</p>

      <div class="pt-hero-actions">
        <!-- When the media is available on Emby we show a "Play" button
             branded with the Emby logo. Otherwise it becomes a "Request"
             button that the parent converts into a modal / API call. -->
        <a
          v-if="item?.emby_url"
          :href="item.emby_url"
          target="_blank"
          class="pt-hero-btn pt-hero-btn--play"
        >
          <img src="/assets/icons/emby.svg" alt="" class="pt-hero-btn-emby" />
          {{ $t('portal.hero.play') }}
        </a>
        <button v-else class="pt-hero-btn pt-hero-btn--play" @click="$emit('request', item)">
          <Plus :size="22" :stroke-width="2.5" />
          {{ $t('portal.card.requestBtn') }}
        </button>
        <button v-if="trailer" class="pt-hero-btn pt-hero-btn--trailer" @click="openLightbox">
          <Video :size="22" />
          {{ $t('portal.detail.watchTrailer') }}
        </button>
        <button
          class="pt-hero-btn pt-hero-btn--info pt-hero-btn--icon"
          :aria-label="$t('portal.moreInfo')"
          @click="$emit('detail', item)"
        >
          <Info :size="24" />
        </button>
      </div>
    </div>

    <button v-if="trailer" class="pt-hero-mute" @click="onMuteToggle">
      <VolumeX v-if="muted" :size="20" />
      <Volume2 v-else :size="20" />
    </button>

    <TrailerLightbox v-if="lightboxOpen && trailer" :trailer="trailer" @close="closeLightbox" />

    <div v-if="totalItems > 1" class="pt-hero-dots">
      <span
        v-for="i in totalItems"
        :key="i"
        class="pt-hero-dot"
        :class="{ active: currentIndex === i - 1 }"
        @click="$emit('goto', i - 1)"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useHeroBannerTrailer } from '@/composables/portal/useHeroBannerTrailer'
import { useHeroCinemaVeil } from '@/composables/portal/useHeroCinemaVeil'
import TrailerLightbox from './TrailerLightbox.vue'
import { isTv } from '@/constants/media'
import { TRAILER_SOURCE } from '@/constants/trailers'
import { Info, Plus, Video, Volume2, VolumeX } from 'lucide-vue-next'

import '@/assets/styles/portal/hero-banner.css'

const props = defineProps({
  item: { type: Object, required: true },
  nextItem: { type: Object, default: null },
  currentIndex: { type: Number, default: 0 },
  totalItems: { type: Number, default: 1 },
  rank: { type: Number, default: 0 },
  isFeatured: { type: Boolean, default: false },
})

const emit = defineEmits([
  'play',
  'detail',
  'goto',
  'sound-on',
  'sound-off',
  'video-ended',
  'request',
])

const {
  trailer,
  muted,
  videoPlaying,
  embyVideoRef,
  playerId,
  loadTrailer,
  prefetchTrailer,
  peekTrailer,
  ensureYTApi,
  toggleMute,
  setMuted,
  setVideoPlaying,
  onEmbyPause,
  onEmbyEnded,
} = useHeroBannerTrailer({ onEnded: () => emit('video-ended') })

const heroRef = ref(null)
const lightboxOpen = ref(false)

// Cinematic black veil between two trailers — asymmetric fade + safety net.
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

const bgStyle = computed(() => {
  const bg = props.item.backdrop || props.item.poster_url || ''
  return bg ? { backgroundImage: `url(${bg})` } : {}
})

function onMuteToggle() {
  toggleMute()
  emit(muted.value ? 'sound-off' : 'sound-on')
}

// Mobile: tapping the hero background (anywhere outside buttons / links)
// toggles the trailer's sound. The dedicated mute button is hidden on
// phones to free up space in the action row. On desktop this handler is a
// no-op because the mute button stays visible and ``window.innerWidth``
// is above the mobile breakpoint.
function onHeroTap(e) {
  if (!trailer.value) return
  if (window.innerWidth >= 640) return
  // Let any actual interactive descendant handle its own click.
  if (e.target.closest('button, a, input, select, textarea')) return
  onMuteToggle()
}

// Opening the fullscreen lightbox must freeze the parent's auto-rotation
// (via the sound-on channel) so the hero doesn't switch under the user
// while they're watching. The previous mute state is restored on close.
let mutedBeforeLightbox = true
function openLightbox() {
  mutedBeforeLightbox = muted.value
  if (!muted.value) setMuted(true)
  lightboxOpen.value = true
  emit('sound-on')
}
function closeLightbox() {
  lightboxOpen.value = false
  if (!mutedBeforeLightbox) {
    setMuted(false)
    // Leave rotation paused — user still has sound on.
  } else {
    emit('sound-off')
  }
}

watch(
  () => props.item?.id,
  () => {
    onItemChange(props.item)
  },
)

// Warm up the trailer URL cache for the next item so the rotation
// resolves instantly — the loading gap under the black veil becomes
// just the YT player's own buffering time.
watch(
  () => props.nextItem?.tmdb_id || props.nextItem?.id,
  () => {
    const n = props.nextItem
    if (!n) return
    prefetchTrailer(n.media_type || 'movie', n.tmdb_id || n.id, n.emby_item_id || null)
  },
  { immediate: true },
)

// Mute the hero trailer when it scrolls out of view, restore prior state
// on scroll-back. Prevents audio from continuing to play "blind" when
// the user scrolls down with sound enabled.
let visObserver = null
let mutedBeforeHide = true
function setupVisibilityObserver() {
  if (!heroRef.value || visObserver) return
  visObserver = new IntersectionObserver(
    ([entry]) => {
      if (entry.isIntersecting && entry.intersectionRatio > 0.1) {
        if (!mutedBeforeHide) {
          setMuted(false)
          emit('sound-on')
        }
      } else {
        mutedBeforeHide = muted.value
        if (!muted.value) {
          setMuted(true)
          emit('sound-off')
        }
      }
    },
    { threshold: [0, 0.1, 0.5] },
  )
  visObserver.observe(heroRef.value)
}

onMounted(async () => {
  try {
    await ensureYTApi()
  } catch {
    /* swallow */
  }
  await startInitial(props.item)
  setupVisibilityObserver()
})

onUnmounted(() => {
  if (visObserver) {
    visObserver.disconnect()
    visObserver = null
  }
  disposeVeil()
})
</script>
