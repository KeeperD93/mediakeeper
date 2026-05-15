<template>
  <section class="pt-top20">
    <h3 class="pt-top20-title">{{ title }}</h3>
    <div ref="trackRef" class="pt-top20-track" @scroll="onScroll">
      <div
        v-for="(item, idx) in items.slice(0, 20)"
        :key="item.id || item.tmdb_id"
        class="pt-top20-card"
        :class="`pt-top20-card--rank-${idx + 1}`"
      >
        <!-- Podium laurel SVG: only rendered for ranks 1/2/3. The rank
             is implied by ordering + the medal-coloured frame around
             the poster, no oversized digit on the side. -->
        <span v-if="idx < 3" class="pt-top20-laurel" aria-hidden="true">
          <svg viewBox="0 0 64 64" fill="none">
            <!-- Medal disc, centered, fills the badge -->
            <circle
              cx="32"
              cy="32"
              r="22"
              fill="currentColor"
              stroke="rgba(0,0,0,0.5)"
              stroke-width="1.5"
            />
            <!-- Inner bevel ring -->
            <circle
              cx="32"
              cy="32"
              r="17"
              fill="none"
              stroke="rgba(0,0,0,0.35)"
              stroke-width="1.2"
            />
            <!-- Engraved star -->
            <path
              d="M32 21 L35 29 L43 29 L36.5 34 L39 42 L32 37 L25 42 L27.5 34 L21 29 L29 29 Z"
              fill="rgba(0,0,0,0.55)"
            />
          </svg>
        </span>
        <!-- Reuse the regular MediaCard so the hover state, "Demander" /
             "Regarder" buttons and availability dot stay perfectly
             consistent with every other carousel on the page. -->
        <MediaCard
          :item="item"
          :width="`${posterWidth}px`"
          :rank="idx + 1 <= 3 ? idx + 1 : null"
          @select="$emit('select', item)"
          @request="$emit('request', item)"
        />
      </div>
    </div>

    <!-- Edge fade gradients (match MediaCarousel / EmbyRecentHero) -->
    <div
      class="pt-edge-fade pt-edge-fade--left"
      :class="{ 'pt-edge-fade--visible': canScrollLeft }"
    />
    <div
      class="pt-edge-fade pt-edge-fade--right"
      :class="{ 'pt-edge-fade--visible': canScrollRight }"
    />

    <!-- Scroll arrows: always visible on desktop when more content
         exists, same glassmorphism style as every other carousel. -->
    <button
      class="pt-carousel-arrow pt-carousel-arrow--left"
      :class="{ 'pt-carousel-arrow--visible': canScrollLeft }"
      :aria-label="$t('common.previous')"
      @click="scroll(-1)"
    >
      <ChevronLeft :size="26" :stroke-width="2.8" />
    </button>
    <button
      class="pt-carousel-arrow pt-carousel-arrow--right"
      :class="{ 'pt-carousel-arrow--visible': canScrollRight }"
      :aria-label="$t('common.next')"
      @click="scroll(1)"
    >
      <ChevronRight :size="26" :stroke-width="2.8" />
    </button>
  </section>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick, watch } from 'vue'
import MediaCard from './MediaCard.vue'
import { ChevronLeft, ChevronRight } from 'lucide-vue-next'

import '@/assets/styles/portal/top20-carousel.css'

const props = defineProps({
  title: { type: String, required: true },
  items: { type: Array, default: () => [] },
})
defineEmits(['select', 'request'])

// Poster width is fixed here so the digit offsets line up. Mobile +
// ultrawide variants are handled in the media queries below.
const posterWidth = 185

const trackRef = ref(null)
// Both start false: if the items list ends up not overflowing the
// track, we don't want to flash a right arrow on first render.
// updateArrows is called as soon as the track is mounted and again
// every time items change.
const canScrollLeft = ref(false)
const canScrollRight = ref(false)

function onScroll() {
  if (!trackRef.value) return
  const el = trackRef.value
  // 32px threshold — matches MediaCarousel / CategoryCards /
  // EmbyRecentHero. Scroll-snap can rest a few pixels off zero when
  // the first card is snapped flush to the scroll-padding edge, so a
  // tight "> 0" threshold would falsely reveal the left arrow at the
  // leftmost position.
  canScrollLeft.value = el.scrollLeft > 32
  canScrollRight.value = el.scrollLeft + el.clientWidth < el.scrollWidth - 32
}

/**
 * Step-scroll by a whole page of fully-visible cards (same algorithm
 * as MediaCarousel) so a click on the arrow never leaves a poster
 * half-cut on either edge. Card width + gap are measured live so this
 * stays correct across breakpoints.
 */
function scroll(dir) {
  const el = trackRef.value
  if (!el) return
  const firstCard = el.querySelector('.pt-top20-card')
  if (!firstCard) return
  const cardRect = firstCard.getBoundingClientRect()
  const trackRect = el.getBoundingClientRect()

  let gap = 16
  const cards = el.querySelectorAll('.pt-top20-card')
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

let resizeObs = null
onMounted(() => {
  if (trackRef.value) {
    resizeObs = new ResizeObserver(onScroll)
    resizeObs.observe(trackRef.value)
    nextTick(onScroll)
  }
})
onUnmounted(() => resizeObs?.disconnect())

// Recompute arrow state when the items list lands (items can arrive
// after mount because the /top20 endpoint is fetched in parallel with
// the rest of the home). Without this the arrows would stay stuck on
// their initial ref values.
watch(
  () => props.items,
  () => {
    nextTick(onScroll)
  },
)
</script>
