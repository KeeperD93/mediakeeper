<template>
  <section ref="sectionRef" class="pt-eh">
    <TrailerLightbox
      v-if="lightboxOpen && candidates.length"
      :trailers="candidates"
      @close="closeLightbox"
    />

    <div class="pt-eh-hero">
      <Transition name="pt-eh-bg-fade">
        <div :key="currentItem?.id" class="pt-eh-hero-bg" :style="bgStyle" />
      </Transition>

      <div class="pt-eh-gradient-top" />
      <div class="pt-eh-gradient-bottom" />

      <div class="pt-eh-content">
        <h3 class="pt-eh-row-title">{{ $t('portal.sections.recentlyAdded') }}</h3>
        <h2 class="pt-eh-item-title">{{ currentItem?.title }}</h2>
        <div class="pt-eh-meta">
          <span v-if="currentItem?.vote" class="pt-eh-vote">★ {{ currentItem.vote }}</span>
          <span v-if="currentItem?.year">{{ currentItem.year }}</span>
        </div>
        <p v-if="currentItem?.overview" class="pt-eh-overview">{{ currentItem.overview }}</p>
        <div class="pt-eh-actions">
          <!-- The hero is informational, not a launch CTA: posters in
               the row below cover both "Lancer" (available) and
               "Demander" (missing). Hero keeps the trailer popup +
               info button. -->
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
import { useTrailer } from '@/composables/portal/useTrailer'
import { ChevronLeft, ChevronRight, Info, Video } from 'lucide-vue-next'

import '@/assets/styles/portal/emby-recent-hero-hero.css'
import '@/assets/styles/portal/emby-recent-hero-row.css'

const props = defineProps({
  items: { type: Array, default: () => [] },
})
const emit = defineEmits(['request', 'detail'])

// Aligned with the main hero (10 s) — both heroes now ship as a
// backdrop slideshow with on-demand trailer popups, so the cadence
// stays consistent across the page.
const ROTATE_MS = 10000
const MAX_VISIBLE = 20

const sectionRef = ref(null)
const trackRef = ref(null)
const currentIndex = ref(0)
const canScrollLeft = ref(false)
const canScrollRight = ref(false)
const isVisible = ref(false)
const lightboxOpen = ref(false)

// Trailer-URL resolution only — never mounts a YouTube IFrame in the
// hero itself. ``resolve`` populates ``trailer`` so the "Bande-annonce"
// button can show / hide based on availability; clicking the button
// opens the fullscreen lightbox where the actual <iframe> finally
// lives. Module-level cache keeps the per-item resolve to one request.
const { trailer, candidates, resolve: resolveTrailer } = useTrailer()

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

async function ensureTrailerResolved() {
  const it = currentItem.value
  if (!it) return
  await resolveTrailer(it.media_type || 'movie', it.tmdb_id || it.id, it.emby_item_id || null)
}

function openLightbox() {
  if (!trailer.value) return
  lightboxOpen.value = true
  stopTimer()
}
function closeLightbox() {
  lightboxOpen.value = false
  if (isVisible.value) startTimer()
}

function onPosterClick(item, idx) {
  currentIndex.value = idx
  // Manual jump: restart the rotation so the user always gets the
  // full ROTATE_MS window on the slide they picked.
  if (isVisible.value && !lightboxOpen.value) startTimer()
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
  // MediaCard now renders its root as `.mk-mediacard` (PR #159 wrapper).
  // The selector keeps `.pt-card` for backward-compat in case a custom
  // call site still uses the legacy class.
  const firstCard = el.querySelector('.mk-mediacard, .pt-card, .pt-eh-seemore')
  if (!firstCard) return
  const cardRect = firstCard.getBoundingClientRect()
  const trackRect = el.getBoundingClientRect()

  let gap = 12
  const cards = el.querySelectorAll('.mk-mediacard, .pt-card, .pt-eh-seemore')
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

watch(
  () => currentItem.value?.id,
  () => {
    if (isVisible.value) ensureTrailerResolved()
  },
)
watch(
  () => props.items.length,
  () => {
    nextTick(updateArrows)
  },
)

let resizeObs = null
let visibilityObs = null
onMounted(() => {
  if (trackRef.value) {
    resizeObs = new ResizeObserver(updateArrows)
    resizeObs.observe(trackRef.value)
    nextTick(updateArrows)
  }
  // Lazy lifecycle: the rotation + the trailer-URL resolve only run
  // while the section is on screen. The trailer subsystem stays
  // limited to a URL lookup — no YouTube IFrame is mounted until the
  // user explicitly clicks the "Bande-annonce" button.
  if (sectionRef.value && typeof IntersectionObserver === 'function') {
    visibilityObs = new IntersectionObserver(
      ([entry]) => {
        const next = !!entry?.isIntersecting
        if (next === isVisible.value) return
        isVisible.value = next
        if (next) {
          startTimer()
          ensureTrailerResolved()
        } else {
          stopTimer()
        }
      },
      { threshold: 0.2 },
    )
    visibilityObs.observe(sectionRef.value)
  } else {
    // Browsers without IntersectionObserver (or jsdom): fall back to
    // the previous eager behaviour so nothing breaks.
    isVisible.value = true
    startTimer()
    ensureTrailerResolved()
  }
})

onBeforeUnmount(() => {
  stopTimer()
  resizeObs?.disconnect()
  visibilityObs?.disconnect()
})
</script>
