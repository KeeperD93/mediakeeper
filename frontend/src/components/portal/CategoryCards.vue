<template>
  <section class="pt-catcards">
    <h3 v-if="title" class="pt-catcards-title">{{ title }}</h3>
    <div ref="trackRef" class="pt-catcards-grid" @scroll="onScroll">
      <div
        v-for="cat in items"
        :key="cat.key || cat.label"
        class="pt-catcard"
        :style="cardStyle(cat)"
        @click="$emit('select', cat)"
      >
        <img v-if="cat.logo" :src="cat.logo" :alt="cat.label" class="pt-catcard-logo" />
        <span v-else class="pt-catcard-label">{{ cat.label }}</span>
      </div>
    </div>

    <!-- Edge fade gradients (match MediaCarousel) -->
    <div
      class="pt-edge-fade pt-edge-fade--left"
      :class="{ 'pt-edge-fade--visible': canScrollLeft }"
    />
    <div
      class="pt-edge-fade pt-edge-fade--right"
      :class="{ 'pt-edge-fade--visible': canScrollRight }"
    />

    <!-- Arrows: always visible on desktop when more content exists,
         matching the MediaCarousel design for consistency. -->
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
import { ChevronLeft, ChevronRight } from 'lucide-vue-next'

import '@/assets/styles/portal/category-cards.css'

const props = defineProps({
  // Optional: when absent, the row renders without a header label.
  title: { type: String, default: '' },
  items: { type: Array, default: () => [] },
})
defineEmits(['select'])

const trackRef = ref(null)
const canScrollLeft = ref(false)
const canScrollRight = ref(false)

function cardStyle(cat) {
  const style = {}
  if (cat.color) style['--cat-color'] = cat.color
  return style
}

function onScroll() {
  const el = trackRef.value
  if (!el) return
  // 32px threshold — see MediaCarousel for the rationale. Keeps the
  // left arrow hidden when the first card is snapped flush.
  canScrollLeft.value = el.scrollLeft > 32
  canScrollRight.value = el.scrollLeft + el.clientWidth < el.scrollWidth - 32
}

/**
 * Step-scroll by a whole "page" of fully-visible cards (same logic
 * as MediaCarousel), so clicking the arrows never leaves a card
 * half-cut on either edge. Card width + gap are measured live from
 * the DOM to stay accurate across breakpoints.
 */
function scroll(dir) {
  const el = trackRef.value
  if (!el) return
  const firstCard = el.querySelector('.pt-catcard')
  if (!firstCard) return
  const cardRect = firstCard.getBoundingClientRect()
  const trackRect = el.getBoundingClientRect()

  let gap = 12
  const cards = el.querySelectorAll('.pt-catcard')
  if (cards.length >= 2) {
    const a = cards[0].getBoundingClientRect()
    const b = cards[1].getBoundingClientRect()
    gap = b.left - a.right
  }
  const step = cardRect.width + gap
  if (step <= 0) return

  const visible = Math.max(1, Math.floor(trackRect.width / step))
  const amount = visible * step
  el.scrollBy({ left: dir * amount, behavior: 'smooth' })
}

// Recompute scroll state when the track resizes (window resize, hero
// banner loading images that change the layout, etc.) AND when the
// items list changes (e.g. platform list swap).
let resizeObs = null
onMounted(() => {
  if (trackRef.value) {
    resizeObs = new ResizeObserver(onScroll)
    resizeObs.observe(trackRef.value)
    // Wait one tick so the initial layout is settled before measuring.
    nextTick(onScroll)
  }
})
onUnmounted(() => resizeObs?.disconnect())

watch(
  () => props.items,
  () => {
    nextTick(onScroll)
  },
)
</script>
